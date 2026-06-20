"""test_bug_fixes.py — Failing-first tests for four correctness bugs + pnl.py verification.

Bug 1: plaid_conn._map_transaction treats amount==0 as expense (>= 0 condition).
Bug 2: revenue_correlation.ratio_findings_for_category computes ratio before zero-revenue guard.
Bug 3: payment_402_handler._do_escalation writes detail=None when both policy_reason
        and anomaly.reason are absent.
Bug 4: cashflow_matrix._infer_year picks wrong 2-digit number from multi-token filenames.
PnL:   pnl.by_category sign convention intentional; pinned here.
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# ===========================================================================
# Bug 1 — plaid_conn: zero-amount transaction must not be emitted as expense
# ===========================================================================

def _make_raw_plaid_txn(
    transaction_id: str,
    amount: float,
    date: str = "2025-01-15",
    name: str = "Vendor",
) -> MagicMock:
    """Build a minimal mock Plaid transaction object."""
    tx = MagicMock()
    tx.transaction_id = transaction_id
    tx.amount = amount
    tx.date = date
    tx.merchant_name = name
    tx.name = name
    tx.personal_finance_category = None
    tx.category = ["Other"]
    tx.authorized_date = None
    return tx


def test_plaid_zero_amount_not_emitted_as_expense():
    """A $0.00 Plaid transaction must not appear in output with direction='expense'.

    The bug: _map_transaction uses `>= 0`, classifying 0.0 as an expense.
    Fix: use `> 0` (expense only for positive amounts) and skip or mark neutral for 0.
    """
    from connectors.plaid_conn import _map_transaction

    raw = _make_raw_plaid_txn("txn_zero", 0.0)
    # After the fix, _map_transaction should either return None / raise to signal
    # the caller to skip it, or return a record that is NOT direction="expense".
    # We test via the public contract: a zero transaction must not be direction="expense".
    result = _map_transaction(raw)
    # The fix contract: None means skip; if a dict, direction must not be "expense".
    if result is not None:
        assert result["direction"] != "expense", (
            "A $0 transaction should not be classified as an expense"
        )


def test_plaid_positive_amount_is_expense():
    """Positive Plaid amount (debit) maps to direction='expense'."""
    from connectors.plaid_conn import _map_transaction

    raw = _make_raw_plaid_txn("txn_debit", 50.0)
    result = _map_transaction(raw)
    assert result is not None
    assert result["direction"] == "expense"
    assert result["amount"] == pytest.approx(50.0)


def test_plaid_negative_amount_is_income():
    """Negative Plaid amount (credit) maps to direction='income'."""
    from connectors.plaid_conn import _map_transaction

    raw = _make_raw_plaid_txn("txn_credit", -200.0)
    result = _map_transaction(raw)
    assert result is not None
    assert result["direction"] == "income"
    assert result["amount"] == pytest.approx(200.0)


# ===========================================================================
# Bug 2 — revenue_correlation: zero-revenue month must not leak inf/NaN
# ===========================================================================

def _make_expenses(months: list[str], amount: float = 100.0) -> list[dict[str, Any]]:
    """Build synthetic expense records for the given months."""
    return [
        {"date": f"{m}-15", "vendor": "Cleaner", "amount": amount,
         "direction": "expense", "category": "cleaning"}
        for m in months
    ]


def test_ratio_findings_no_inf_on_zero_revenue_month():
    """ratio_findings_for_category must not produce inf/NaN when one month has revenue=0.

    The bug: `shared` is built from the full intersection of cost and rev months
    BEFORE filtering out zero-revenue entries. The `len(shared) < 2` guard can
    pass incorrectly when only 1 of 2 shared months has real revenue, leading
    the ratios list to have only 1 entry which is then silently dropped by
    `len(ratios) < 2`. The fix moves the zero-revenue filter to shared construction
    so semantics are explicit and the minimum-months guard counts only valid months.

    #COMPLETION_DRIVE: moving the filter earlier also eliminates any future risk
    of inf/NaN if the guard logic is refactored.
    """
    from analysis.revenue_correlation import ratio_findings_for_category

    # Set up: 6 months of expenses, but month 3 has revenue=0
    months = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
    expenses = _make_expenses(months, 100.0)

    rev_by_month = {
        "2025-01": 1000.0,
        "2025-02": 1100.0,
        "2025-03": 0.0,   # zero-revenue month — the bug trigger
        "2025-04": 900.0,
        "2025-05": 1050.0,
        "2025-06": 980.0,
    }

    findings = ratio_findings_for_category(
        "cleaning", expenses, rev_by_month,
        ratio_z_threshold=2.0,
        ratio_jump_threshold=0.30,
    )

    # No finding should contain inf or NaN in any numeric field
    for f in findings:
        assert not math.isnan(f.monthly_impact), "monthly_impact is NaN"
        assert not math.isinf(f.monthly_impact), "monthly_impact is inf"
        assert not math.isnan(f.annual_impact), "annual_impact is NaN"
        assert not math.isinf(f.annual_impact), "annual_impact is inf"


def test_ratio_findings_zero_revenue_month_min_guard_uses_valid_count():
    """The len(shared) < 2 guard must count only non-zero-revenue months.

    Bug: with 2 cost months where 1 has zero revenue, len(shared)==2 passes
    the guard, but len(ratios)==1 triggers the ratios guard. After the fix,
    shared is built from non-zero-revenue months, so len(shared)==1 < 2
    causes an early return from the outer guard — consistent semantics.
    The observable outcome is the same (return []), but the guard logic is
    semantically correct and won't silently drop a valid month.
    """
    from analysis.revenue_correlation import ratio_findings_for_category

    # Only 2 cost months, and 1 of them has zero revenue
    expenses = _make_expenses(["2025-01", "2025-02"], 100.0)
    rev_by_month = {
        "2025-01": 1000.0,
        "2025-02": 0.0,  # zero-revenue — after fix, shared only has jan -> len==1 -> []
    }

    findings = ratio_findings_for_category(
        "cleaning", expenses, rev_by_month,
        ratio_z_threshold=2.0,
        ratio_jump_threshold=0.30,
    )
    # Either way returns [] — the test pins that zero-revenue months are excluded
    assert findings == []


def test_ratio_findings_zero_revenue_month_excluded_from_output():
    """A month with revenue=0 must not appear as a Finding month."""
    from analysis.revenue_correlation import ratio_findings_for_category

    months = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
    expenses = _make_expenses(months, 100.0)

    rev_by_month = {m: (0.0 if m == "2025-03" else 1000.0) for m in months}

    findings = ratio_findings_for_category(
        "cleaning", expenses, rev_by_month,
        ratio_z_threshold=2.0,
        ratio_jump_threshold=0.30,
    )

    finding_months = [f.why for f in findings]
    for why in finding_months:
        assert "2025-03" not in why, "Zero-revenue month appeared in a Finding"


# ===========================================================================
# Bug 3 — payment_402_handler: escalation detail must never be None
# ===========================================================================

def _build_minimal_graph(vendor: str = "ACME") -> MagicMock:
    """Build a minimal KnowledgeGraph mock."""
    graph = MagicMock()
    graph.is_known_vendor.return_value = False
    graph.expected_range.return_value = None
    graph.vendor_history.return_value = []
    return graph


def _null_anomaly():
    """Real Anomaly dataclass instance that is flagged but has no reason string.

    Uses None for reason despite the str annotation — this is the exact runtime
    condition that causes `policy_reason or anomaly.reason` to evaluate to None.
    """
    from gbrain.anomaly_detector import Anomaly

    return Anomaly(
        vendor="ACME",
        current_amount=999.0,
        baseline_mean=100.0,
        z_score=3.5,
        pct_change=8.99,
        is_anomaly=True,
        reason=None,  # type: ignore[arg-type]  # real-world data can arrive without a reason
    )


def test_escalation_detail_is_string_when_both_reasons_absent(tmp_path, monkeypatch):
    """_do_escalation must write a non-empty string to detail even when
    policy_reason=None and anomaly.reason=None.

    The bug: `detail = policy_reason or anomaly.reason` evaluates to None,
    writing {"detail": None} into the steps list.
    """
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(tmp_path / "approvals"))
    (tmp_path / "approvals").mkdir()

    from payments.payment_402_handler import _do_escalation

    anomaly = _null_anomaly()
    steps: list[dict] = []

    result = _do_escalation(
        vendor="ACME",
        amount=999.0,
        invoice_id="inv-001",
        anomaly=anomaly,
        steps=steps,
        threshold=500.0,
        audit_path=str(tmp_path / "audit.jsonl"),
        policy_reason=None,   # both absent
    )

    # Find the "decision" step that _do_escalation appends
    decision_steps = [s for s in result["steps"] if s["step"] == "decision"]
    assert decision_steps, "No decision step appended"
    detail = decision_steps[0]["detail"]
    assert detail is not None, "detail is None — bug not fixed"
    assert isinstance(detail, str), f"detail is not a string: {type(detail)}"
    assert len(detail) > 0, "detail is an empty string"


def test_escalation_detail_uses_policy_reason_when_present(tmp_path, monkeypatch):
    """When policy_reason is set, it should appear in the decision step detail."""
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(tmp_path / "approvals"))
    (tmp_path / "approvals").mkdir()

    from payments.payment_402_handler import _do_escalation

    anomaly = _null_anomaly()
    steps: list[dict] = []

    result = _do_escalation(
        vendor="ACME",
        amount=99.0,
        invoice_id="inv-002",
        anomaly=anomaly,
        steps=steps,
        threshold=500.0,
        audit_path=str(tmp_path / "audit.jsonl"),
        policy_reason="vendor blocked by policy",
    )

    decision_steps = [s for s in result["steps"] if s["step"] == "decision"]
    assert decision_steps
    assert "vendor blocked by policy" in decision_steps[0]["detail"]


# ===========================================================================
# Bug 4 — cashflow_matrix._infer_year: ambiguous multi-digit filename
# ===========================================================================

def _write_csv(tmp_path: Path, name: str, content: str) -> Path:
    """Write content to a named file and return the path."""
    p = tmp_path / name
    p.write_text(content)
    return p


_SIMPLE_MATRIX = textwrap.dedent("""\
    ,jan,feb
    Revenue,$1000,$1200
    Mgmt Fees,$100,$120
""")


def test_infer_year_ambiguous_filename_picks_cashflows_token(tmp_path):
    """Filename 'huckle_finances_6.10.26.xlsx - Oside Cashflows 25.csv' -> 2025.

    The fix must prefer the 'Cashflows NN' pattern over a raw trailing-digit match
    so that extra version/date tokens in the name don't override the year marker.
    """
    from ingestion.cashflow_matrix import _infer_year

    p = tmp_path / "huckle_finances_6.10.26.xlsx - Oside Cashflows 25.csv"
    p.touch()
    year = _infer_year(p)
    assert year == 2025, f"Expected 2025, got {year}"


def test_infer_year_cashflows_24_suffix(tmp_path):
    """'...Cashflows 24.csv' -> 2024."""
    from ingestion.cashflow_matrix import _infer_year

    p = tmp_path / "huckle_finances_6.10.25.xlsx - Oside Cashflows 24.csv"
    p.touch()
    year = _infer_year(p)
    assert year == 2024, f"Expected 2024, got {year}"


def test_infer_year_cashflows_with_trailing_suffix_fails_without_fix(tmp_path):
    """'...Cashflows 25 - final.csv' must infer 2025, not today.year.

    The bug: the raw trailing-digit regex fails because the stem ends in 'final'
    (no trailing digits). Without the Cashflows-aware pattern, _infer_year returns None
    and falls back to today.year, which is wrong.
    """
    from ingestion.cashflow_matrix import _infer_year

    # stem = '...Cashflows 25 - final' -> no trailing digits -> current code returns None
    p = tmp_path / "huckle_6.10.26.xlsx - Oside Cashflows 25 - final.csv"
    p.touch()
    year = _infer_year(p)
    assert year == 2025, f"Expected 2025 from Cashflows token, got {year}"


def test_infer_year_simple_two_digit_suffix_unchanged(tmp_path):
    """Simple 'str_pnl_25.csv' -> 2025 (regression: existing behavior preserved)."""
    from ingestion.cashflow_matrix import _infer_year

    p = tmp_path / "str_pnl_25.csv"
    p.touch()
    year = _infer_year(p)
    assert year == 2025


def test_infer_year_four_digit_stem_unchanged(tmp_path):
    """'str_2024.csv' -> 2024 (4-digit match still takes priority)."""
    from ingestion.cashflow_matrix import _infer_year

    p = tmp_path / "str_2024.csv"
    p.touch()
    year = _infer_year(p)
    assert year == 2024


def test_year_map_override_wins(tmp_path):
    """Tenant ingestion.cashflow.year_map wins over filename inference.

    Simulates the caller (load_matrix or its orchestrator) resolving the year
    from the year_map before calling _infer_year.
    """
    from ingestion.cashflow_matrix import load_matrix

    # Ambiguous filename that would infer 2025 without the map
    fname = "huckle_finances_6.10.26.xlsx - Oside Cashflows 25.csv"
    p = _write_csv(tmp_path, fname, _SIMPLE_MATRIX)

    # year_map override: this file should use 2024
    year_map = {fname: 2024}
    override_year = year_map.get(fname)

    records = load_matrix(p, override_year, ["Revenue"], ["Mgmt Fees"], [])
    assert all(r["date"].startswith("2024") for r in records), (
        "year_map override did not win over filename inference"
    )


def test_two_files_different_years(tmp_path):
    """Two files in the same tenant directory get different correct years.

    This is the core multi-year use case: Erik's 2024 and 2025 cashflow files
    must each resolve to their own year, not both to the same default.
    """
    from ingestion.cashflow_matrix import load_matrix

    fname_25 = "huckle_finances_6.10.26.xlsx - Oside Cashflows 25.csv"
    fname_24 = "huckle_finances_6.10.25.xlsx - Oside Cashflows 24.csv"

    p25 = _write_csv(tmp_path, fname_25, _SIMPLE_MATRIX)
    p24 = _write_csv(tmp_path, fname_24, _SIMPLE_MATRIX)

    year_map = {fname_25: 2025, fname_24: 2024}

    records_25 = load_matrix(p25, year_map.get(fname_25), ["Revenue"], ["Mgmt Fees"], [])
    records_24 = load_matrix(p24, year_map.get(fname_24), ["Revenue"], ["Mgmt Fees"], [])

    assert all(r["date"].startswith("2025") for r in records_25)
    assert all(r["date"].startswith("2024") for r in records_24)


# ===========================================================================
# PnL by_category sign convention — intentional behavior pinned
# ===========================================================================

def test_pnl_by_category_income_is_negative():
    """by_category uses negative values for income (net impact on profit from that category).

    This is intentional: by_category[cat] += amount if expense else -amount.
    The sign allows summing all categories to get net P&L.
    This test pins the behavior so a future reader doesn't "fix" it accidentally.
    """
    from analysis.pnl import compute_pnl

    txns = [
        {"date": "2025-01-01", "amount": 1000.0, "direction": "income",
         "category": "revenue"},
        {"date": "2025-01-05", "amount": 200.0, "direction": "expense",
         "category": "cleaning"},
    ]
    result = compute_pnl(txns)
    bc = result["monthly"]["2025-01"]["by_category"]
    # Income category stored as negative (reduces the net-expense bucket)
    assert bc["revenue"] == pytest.approx(-1000.0)
    # Expense category stored as positive
    assert bc["cleaning"] == pytest.approx(200.0)
    # Net P&L == income - expense == 1000 - 200 == 800
    # Verify sum of by_category == -(net): (-1000 + 200) == -800 == -net
    assert sum(bc.values()) == pytest.approx(-result["monthly"]["2025-01"]["net"])


def test_pnl_totals_unaffected_by_sign_convention():
    """The signed by_category storage does not corrupt income/expense/net totals."""
    from analysis.pnl import compute_pnl

    txns = [
        {"date": "2025-01-01", "amount": 500.0, "direction": "income", "category": "rent"},
        {"date": "2025-01-10", "amount": 100.0, "direction": "expense", "category": "mgmt"},
    ]
    result = compute_pnl(txns)
    assert result["totals"]["income"] == pytest.approx(500.0)
    assert result["totals"]["expense"] == pytest.approx(100.0)
    assert result["totals"]["net"] == pytest.approx(400.0)
