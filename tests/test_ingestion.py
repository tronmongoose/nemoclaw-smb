"""test_ingestion.py — Offline tests for ingestion adapters and loader.

Covers:
- chase_csv sign convention (charge=expense, credit=income)
- spreadsheet column mapping (explicit + inferred)
- load_transactions dispatch and dedup
- route_llm stays local for a restricted tenant (no frontier import)
"""

from __future__ import annotations

import csv
import io
import textwrap
from pathlib import Path

import pytest

from ingestion.chase_csv import is_chase_csv, parse_chase_csv
from ingestion.spreadsheet import parse_spreadsheet


# ---------------------------------------------------------------------------
# Chase CSV helpers
# ---------------------------------------------------------------------------

_CHASE_HEADER = "Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n"


def _write_chase(tmp_path: Path, rows: list[dict]) -> Path:
    """Write a Chase-format CSV and return the path."""
    f = tmp_path / "chase.csv"
    lines = [_CHASE_HEADER.strip()]
    for r in rows:
        lines.append(
            f"{r.get('Transaction Date','2025-01-01')},"
            f"{r.get('Post Date','2025-01-02')},"
            f"{r.get('Description','Vendor')},"
            f"{r.get('Category','')},"
            f"{r.get('Type','Sale')},"
            f"{r.get('Amount','0')},"
            f"{r.get('Memo','')}"
        )
    f.write_text("\n".join(lines))
    return f


# ---------------------------------------------------------------------------
# Chase CSV: sign convention
# ---------------------------------------------------------------------------

def test_chase_charge_is_expense(tmp_path):
    """A Chase charge (negative Amount) maps to direction='expense'."""
    f = _write_chase(tmp_path, [{"Description": "Coffee Shop", "Amount": "-12.50", "Category": "Food"}])
    txns = parse_chase_csv(f)
    assert len(txns) == 1
    t = txns[0]
    assert t["direction"] == "expense"
    assert t["amount"] == pytest.approx(12.50)


def test_chase_payment_is_income(tmp_path):
    """A Chase payment (positive Amount) maps to direction='income'."""
    f = _write_chase(tmp_path, [{"Description": "Payment Thank You", "Amount": "500.00", "Type": "Payment"}])
    txns = parse_chase_csv(f)
    assert txns[0]["direction"] == "income"
    assert txns[0]["amount"] == pytest.approx(500.00)


def test_chase_amount_always_positive(tmp_path):
    """Parsed amount is always a positive float regardless of Chase sign."""
    f = _write_chase(tmp_path, [
        {"Description": "Vendor A", "Amount": "-99.99"},
        {"Description": "Refund", "Amount": "50.00"},
    ])
    txns = parse_chase_csv(f)
    assert all(t["amount"] >= 0 for t in txns)


def test_chase_vendor_from_description(tmp_path):
    """vendor field is populated from the Description column."""
    f = _write_chase(tmp_path, [{"Description": "Amazon Prime", "Amount": "-14.99"}])
    txns = parse_chase_csv(f)
    assert txns[0]["vendor"] == "Amazon Prime"


def test_is_chase_csv_detects_header(tmp_path):
    """is_chase_csv returns True for a file with the canonical Chase header."""
    f = _write_chase(tmp_path, [])
    assert is_chase_csv(f) is True


def test_is_chase_csv_rejects_non_chase(tmp_path):
    """is_chase_csv returns False for a generic CSV."""
    f = tmp_path / "generic.csv"
    f.write_text("date,vendor,amount\n2025-01-01,Acme,100.00\n")
    assert is_chase_csv(f) is False


def test_chase_source_field_has_filename(tmp_path):
    """source field contains the filename for traceability."""
    f = _write_chase(tmp_path, [{"Description": "X", "Amount": "-1.00"}])
    txns = parse_chase_csv(f)
    assert "chase.csv" in txns[0]["source"]


# ---------------------------------------------------------------------------
# Spreadsheet adapter: column mapping
# ---------------------------------------------------------------------------

def _write_csv(tmp_path: Path, header: list[str], rows: list[list[str]], name: str = "data.csv") -> Path:
    """Write a generic CSV file and return path."""
    f = tmp_path / name
    lines = [",".join(header)]
    for r in rows:
        lines.append(",".join(r))
    f.write_text("\n".join(lines))
    return f


def test_spreadsheet_explicit_column_map(tmp_path):
    """Explicit column map resolves date/vendor/amount correctly."""
    f = _write_csv(tmp_path, ["Dt", "Merchant", "Cost", "Cat"], [
        ["2025-03-01", "Acme Corp", "123.45", "Supplies"],
    ])
    col_map = {"date": "Dt", "vendor": "Merchant", "amount": "Cost", "category": "Cat"}
    txns = parse_spreadsheet(f, column_map=col_map)
    assert len(txns) == 1
    assert txns[0]["date"] == "2025-03-01"
    assert txns[0]["vendor"] == "Acme Corp"
    assert txns[0]["amount"] == pytest.approx(123.45)
    assert txns[0]["category"] == "Supplies"


def test_spreadsheet_inferred_headers(tmp_path):
    """Inferred headers (matching known names) work without explicit map."""
    f = _write_csv(tmp_path, ["date", "vendor", "amount"], [
        ["2025-04-01", "SupplyCo", "88.00"],
    ])
    txns = parse_spreadsheet(f)
    assert txns[0]["vendor"] == "SupplyCo"
    assert txns[0]["amount"] == pytest.approx(88.00)


def test_spreadsheet_negative_amount_is_expense(tmp_path):
    """Negative amount without explicit direction column maps to expense."""
    f = _write_csv(tmp_path, ["date", "vendor", "amount"], [
        ["2025-05-01", "Gas Co", "-55.00"],
    ])
    txns = parse_spreadsheet(f)
    assert txns[0]["direction"] == "expense"
    assert txns[0]["amount"] == pytest.approx(55.00)


def test_spreadsheet_positive_amount_is_income(tmp_path):
    """Positive amount without explicit direction column maps to income."""
    f = _write_csv(tmp_path, ["date", "vendor", "amount"], [
        ["2025-05-01", "Tenant Payment", "2000.00"],
    ])
    txns = parse_spreadsheet(f)
    assert txns[0]["direction"] == "income"


def test_spreadsheet_explicit_direction_column(tmp_path):
    """Explicit direction column value overrides amount sign."""
    f = _write_csv(tmp_path, ["date", "vendor", "amount", "direction"], [
        ["2025-06-01", "Corp X", "500.00", "expense"],
    ])
    txns = parse_spreadsheet(f, column_map={"direction": "direction"})
    assert txns[0]["direction"] == "expense"


# ---------------------------------------------------------------------------
# load_transactions: dispatch + dedup
# ---------------------------------------------------------------------------

def test_load_transactions_dispatches_to_chase(tmp_path):
    """load_transactions uses chase adapter when Chase header is detected."""
    f = _write_chase(tmp_path, [{"Description": "Netflix", "Amount": "-15.99"}])
    from agent.tenancy import Tenant
    from ingestion.loader import load_transactions

    t = Tenant(
        slug="t", data_root=str(tmp_path), llm_routing="local",
        sensitivity="internal", mode="advisory",
    )
    txns = load_transactions(t)
    assert len(txns) == 1
    assert txns[0]["source"].startswith("chase:")


def test_load_transactions_deduplicates(tmp_path):
    """Duplicate (date, vendor, amount) rows are collapsed to one."""
    # Write two CSV files with an overlapping row
    f1 = _write_csv(tmp_path, ["date", "vendor", "amount"], [
        ["2025-01-01", "Acme", "100.00"],
    ], name="a.csv")
    f2 = _write_csv(tmp_path, ["date", "vendor", "amount"], [
        ["2025-01-01", "Acme", "100.00"],
        ["2025-01-02", "Beta", "50.00"],
    ], name="b.csv")

    from agent.tenancy import Tenant
    from ingestion.loader import load_transactions

    t = Tenant(
        slug="t", data_root=str(tmp_path), llm_routing="local",
        sensitivity="internal", mode="advisory",
    )
    txns = load_transactions(t)
    assert len(txns) == 2


def test_load_transactions_sorted_by_date(tmp_path):
    """Returned transactions are sorted ascending by date."""
    f = _write_csv(tmp_path, ["date", "vendor", "amount"], [
        ["2025-03-01", "C", "1.00"],
        ["2025-01-01", "A", "1.00"],
        ["2025-02-01", "B", "1.00"],
    ])
    from agent.tenancy import Tenant
    from ingestion.loader import load_transactions

    t = Tenant(
        slug="t", data_root=str(tmp_path), llm_routing="local",
        sensitivity="internal", mode="advisory",
    )
    txns = load_transactions(t)
    dates = [x["date"] for x in txns]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# route_llm: restricted tenant stays local — no frontier import possible
# ---------------------------------------------------------------------------

def test_route_llm_restricted_tenant_is_local(tmp_path):
    """route_llm for a restricted tenant returns a local callable, not a frontier one."""
    from agent.claw_router import route_llm
    from agent.local_client import call_local
    from agent.tenancy import Tenant

    t = Tenant(
        slug="str", data_root=str(tmp_path),
        llm_routing="local", sensitivity="restricted", mode="advisory",
    )
    fn = route_llm(t)
    # Must be call_local itself (no local_model pin on this tenant)
    assert fn is call_local


def test_route_llm_pinned_model_wraps_call_local(tmp_path):
    """A tenant with local_model set returns a partial wrapping call_local."""
    import functools
    from agent.claw_router import route_llm
    from agent.tenancy import Tenant

    t = Tenant(
        slug="str", data_root=str(tmp_path),
        llm_routing="local", sensitivity="restricted", mode="advisory",
        local_model="gemma4:26b",
    )
    fn = route_llm(t)
    assert isinstance(fn, functools.partial)
    # The wrapped function must be call_local
    from agent.local_client import call_local
    assert fn.func is call_local
    assert fn.keywords.get("model") == "gemma4:26b"
