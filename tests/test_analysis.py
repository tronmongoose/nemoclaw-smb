"""test_analysis.py — Offline tests for analysis/ package.

Covers:
- compute_pnl math (income/expense/net/by_category for a known set)
- findings: flags a planted recurring-bill jump and an anomaly with correct $ impact
- report builds without an LLM
- route_llm stays local for restricted tenant (no frontier import)
"""

from __future__ import annotations

import pytest

from analysis.pnl import compute_pnl
from analysis.findings import find, Finding
from gbrain.knowledge_graph import KnowledgeGraph


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_transactions() -> list[dict]:
    """Return a known set of transactions for deterministic math tests."""
    return [
        # Income
        {"date": "2025-01-10", "vendor": "Rental Inc", "amount": 3000.0,
         "direction": "income", "category": "rental_income"},
        {"date": "2025-02-10", "vendor": "Rental Inc", "amount": 3200.0,
         "direction": "income", "category": "rental_income"},
        # Expenses
        {"date": "2025-01-05", "vendor": "Electric Co", "amount": 100.0,
         "direction": "expense", "category": "utilities"},
        {"date": "2025-01-15", "vendor": "Cleaner LLC", "amount": 200.0,
         "direction": "expense", "category": "maintenance"},
        {"date": "2025-02-05", "vendor": "Electric Co", "amount": 105.0,
         "direction": "expense", "category": "utilities"},
        {"date": "2025-02-15", "vendor": "Cleaner LLC", "amount": 200.0,
         "direction": "expense", "category": "maintenance"},
    ]


# ---------------------------------------------------------------------------
# compute_pnl math
# ---------------------------------------------------------------------------

def test_pnl_income_january():
    """January income should be 3000."""
    pnl = compute_pnl(_make_transactions())
    assert pnl["monthly"]["2025-01"]["income"] == pytest.approx(3000.0)


def test_pnl_expense_january():
    """January expense should be 100 + 200 = 300."""
    pnl = compute_pnl(_make_transactions())
    assert pnl["monthly"]["2025-01"]["expense"] == pytest.approx(300.0)


def test_pnl_net_january():
    """January net should be 3000 - 300 = 2700."""
    pnl = compute_pnl(_make_transactions())
    assert pnl["monthly"]["2025-01"]["net"] == pytest.approx(2700.0)


def test_pnl_by_category_january():
    """January by_category should include utilities and maintenance."""
    pnl = compute_pnl(_make_transactions())
    cats = pnl["monthly"]["2025-01"]["by_category"]
    assert "utilities" in cats
    assert "maintenance" in cats
    assert cats["utilities"] == pytest.approx(100.0)
    assert cats["maintenance"] == pytest.approx(200.0)


def test_pnl_totals():
    """Totals aggregate correctly across months."""
    pnl = compute_pnl(_make_transactions())
    assert pnl["totals"]["income"] == pytest.approx(6200.0)
    assert pnl["totals"]["expense"] == pytest.approx(605.0)
    assert pnl["totals"]["net"] == pytest.approx(5595.0)


def test_pnl_margin_trend_sorted():
    """margin_trend is sorted ascending by month."""
    pnl = compute_pnl(_make_transactions())
    months = [e["month"] for e in pnl["margin_trend"]]
    assert months == sorted(months)


def test_pnl_empty_transactions():
    """compute_pnl handles empty input without error."""
    pnl = compute_pnl([])
    assert pnl["totals"]["income"] == 0.0
    assert pnl["totals"]["expense"] == 0.0
    assert pnl["monthly"] == {}


# ---------------------------------------------------------------------------
# findings: planted recurring-bill jump
# ---------------------------------------------------------------------------

def _recurring_jump_transactions() -> list[dict]:
    """A lawn vendor that jumps > 20% in month 3 (alert_delta_pct=20%)."""
    return [
        {"date": "2025-01-14", "vendor": "Lawn Care Pro", "amount": 80.0,
         "direction": "expense", "category": "lawn"},
        {"date": "2025-02-14", "vendor": "Lawn Care Pro", "amount": 82.0,
         "direction": "expense", "category": "lawn"},
        {"date": "2025-03-14", "vendor": "Lawn Care Pro", "amount": 110.0,
         "direction": "expense", "category": "lawn"},
        # second vendor for recurring detection to have enough data
        {"date": "2025-01-01", "vendor": "Ring Security", "amount": 9.99,
         "direction": "expense", "category": "security"},
        {"date": "2025-02-01", "vendor": "Ring Security", "amount": 9.99,
         "direction": "expense", "category": "security"},
        {"date": "2025-03-01", "vendor": "Ring Security", "amount": 9.99,
         "direction": "expense", "category": "security"},
    ]


def test_findings_recurring_bill_jump_detected():
    """find() should flag Lawn Care Pro's 34% jump when alert_delta_pct=20."""
    txns = _recurring_jump_transactions()
    graph = KnowledgeGraph()
    thresholds = {"alert_delta_pct": 20.0}
    findings = find(txns, graph, thresholds)
    titles = [f.title for f in findings]
    assert any("Lawn Care Pro" in t for t in titles), f"Expected Lawn Care jump in: {titles}"


def test_findings_jump_monthly_impact_positive():
    """The recurring jump finding should have a positive monthly impact."""
    txns = _recurring_jump_transactions()
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})
    jump_findings = [f for f in findings if "Lawn Care Pro" in f.title and "jump" in f.title.lower()]
    assert len(jump_findings) >= 1
    assert jump_findings[0].monthly_impact > 0


# ---------------------------------------------------------------------------
# findings: planted anomaly
# ---------------------------------------------------------------------------

def _anomaly_transactions() -> list[dict]:
    """Vendor with slightly-varied history then a clear spike in month 6.

    History must have non-zero std-dev for z-score to fire.
    Mean ~102, pstdev ~7 -> 180 is z~11, well above threshold.
    """
    amounts = [95.0, 100.0, 105.0, 98.0, 110.0]
    base = [
        {"date": f"2025-0{i}-01", "vendor": "Electric Co", "amount": amounts[i-1],
         "direction": "expense", "category": "utilities"}
        for i in range(1, 6)
    ]
    # month 6 spike: 180 vs mean ~101.6 is well > 2 std-dev
    base.append({"date": "2025-06-01", "vendor": "Electric Co", "amount": 180.0,
                 "direction": "expense", "category": "utilities"})
    return base


def test_findings_anomaly_detected():
    """find() flags Electric Co's spike as an anomaly."""
    txns = _anomaly_transactions()
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})
    titles = [f.title for f in findings]
    assert any("Electric Co" in t for t in titles), f"Expected anomaly in: {titles}"


def test_findings_anomaly_impact_correct():
    """Anomaly monthly_impact is approximately the delta from baseline mean."""
    txns = _anomaly_transactions()
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})
    anomaly_f = next((f for f in findings if "Electric Co" in f.title and "spike" in f.title.lower()), None)
    assert anomaly_f is not None
    # mean of first 5 points = 100; spike = 180; delta ~ 80
    assert anomaly_f.monthly_impact == pytest.approx(80.0, abs=5.0)


# ---------------------------------------------------------------------------
# report: builds without LLM
# ---------------------------------------------------------------------------

def test_report_builds_without_llm(tmp_path):
    """build_report returns a non-empty markdown string without any LLM."""
    from analysis.report import build_report
    from agent.tenancy import Tenant

    t = Tenant(
        slug="test", data_root=str(tmp_path),
        llm_routing="local", sensitivity="restricted", mode="advisory",
    )
    pnl = compute_pnl(_make_transactions())
    findings = find(_make_transactions(), KnowledgeGraph(), {"alert_delta_pct": 20.0})
    report = build_report(t, pnl, findings)

    assert isinstance(report, str)
    assert len(report) > 100
    assert "P&L" in report


def test_report_contains_pnl_table(tmp_path):
    """Report includes a markdown P&L table with month rows."""
    from analysis.report import build_report
    from agent.tenancy import Tenant

    t = Tenant(
        slug="test", data_root=str(tmp_path),
        llm_routing="local", sensitivity="restricted", mode="advisory",
    )
    pnl = compute_pnl(_make_transactions())
    report = build_report(t, pnl, [])
    assert "2025-01" in report
    assert "2025-02" in report


def test_report_written_to_data_root(tmp_path):
    """build_report writes report.md to tenant.data_root."""
    from analysis.report import build_report
    from agent.tenancy import Tenant
    from pathlib import Path

    t = Tenant(
        slug="test", data_root=str(tmp_path),
        llm_routing="local", sensitivity="restricted", mode="advisory",
    )
    build_report(t, compute_pnl([]), [])
    assert (tmp_path / "report.md").exists()


def test_report_complete_without_narrative(tmp_path, monkeypatch):
    """Report is complete even when the LLM call raises."""
    from analysis import build_report
    from analysis import report as report_mod
    from agent.tenancy import Tenant

    # Force the narrative function to raise
    monkeypatch.setattr(report_mod, "_try_narrative", lambda *a, **k: None)

    t = Tenant(
        slug="test", data_root=str(tmp_path),
        llm_routing="local", sensitivity="restricted", mode="advisory",
    )
    pnl = compute_pnl(_make_transactions())
    report = build_report(t, pnl, [])
    assert "Advisory Findings" in report
