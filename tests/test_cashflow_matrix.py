"""test_cashflow_matrix.py — Offline tests for the cashflow matrix ingestion adapter.

Covers:
- is_matrix detects month-header CSVs; rejects Chase and generic headers
- load_matrix melts the right record count
- Revenue -> income, SDGE -> expense
- Parenthetical amounts parsed as negative (abs stored, direction preserved)
- $ and commas stripped from amounts
- Total, projection, and trailing blank columns are ignored
- Skip rows (Net to owner, Notes, Total, Avg, Months, blank) excluded
- Year inferred from filename "str_pnl_25.csv" -> 2025
- Date is the last day of the correct month
- include-glob in loader filters files to avoid double-counting
- compute_pnl + find run on melted records and produce sensible output
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ingestion.cashflow_matrix import (
    DEFAULT_EXPENSE,
    DEFAULT_INCOME,
    DEFAULT_SKIP,
    is_matrix,
    load_matrix,
)

# ---------------------------------------------------------------------------
# Minimal synthetic matrix CSV used across multiple tests
# ---------------------------------------------------------------------------

_MATRIX_CSV = textwrap.dedent("""\
    ,jan,feb,march,apr,may,jun,july,aug,sept,oct,Nov,dec,Total,Projected Summer Low,Projected Winter Low,
    Revenue,$2800,$2650,$3100,$2950,$3200,$3800,$4100,$4000,$3500,$2900,$2700,$2500,$38200,,
    Pet fees,$150,$100,$200,$125,$175,$225,$300,$250,$175,$100,$125,$75,$2000,,
    Parents/Friends Stay,,$200,,,$100,,,,$150,,,,$450,,
    Mgmt Fees,$280,$265,$310,$295,$320,$380,$410,$400,$350,$290,$270,$250,$3820,,
    Yard care X2 a  month,$80,$80,$80,$80,$80,$80,$80,$80,$80,$80,$80,$80,$960,,
    Oceanside Munirevs,$45,$45,$45,$45,$45,$45,$45,$45,$45,$45,$45,$45,$540,,
    Water+water waste (COO),$62,$58,$71,$65,$74,$89,$95,$88,$76,$63,$59,$55,$855,,
    City Waste (waste mgmt),$35,$35,$35,$35,$35,$35,$35,$35,$35,$35,$35,$35,$420,,
    Internet (7962),$80,$80,$80,$80,$80,$80,$80,$80,$80,$80,$80,$80,$960,,
    Electricity+ Gas (SDGE),$210,$195,$175,$155,$140,$180,$230,$225,$190,$165,$200,$220,$2285,,
    Instacart+Amazon,$45,$30,$55,$40,$60,$75,$90,$85,$65,$35,$40,$25,$645,,
    Owner Exp (extra),,$100,,,$200,,,$150,,,$100,,$550,,
    Net to owner,$2113,$2062,$2549,$2280,$2641,$3136,$3425,$3225,$2804,$2207,$1996,$1790,$29228,,
    Notes,,,,,,,,,,,,,,,,
    Total,,,,,,,,,,,,,,,,
    Avg Total Proceeds/Month,,,,,,,,,,,,,,,,
    Months,,,,,,,,,,,,,,,,
""")

_CHASE_HEADER_CSV = textwrap.dedent("""\
    Transaction Date,Post Date,Description,Category,Type,Amount,Memo
    01/05/2025,01/06/2025,Coffee Shop,Food,Sale,-12.50,
""")

_GENERIC_CSV = textwrap.dedent("""\
    date,vendor,amount
    2025-01-01,Acme,100.00
""")


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write content to a named file under tmp_path and return the path."""
    p = tmp_path / name
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# is_matrix detection
# ---------------------------------------------------------------------------

def test_is_matrix_detects_month_header(tmp_path):
    """is_matrix returns True for a file whose header contains month tokens."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    assert is_matrix(f) is True


def test_is_matrix_rejects_chase_header(tmp_path):
    """is_matrix returns False for a Chase CSV whose header has 'Transaction Date'."""
    f = _write(tmp_path, "chase.csv", _CHASE_HEADER_CSV)
    assert is_matrix(f) is False


def test_is_matrix_rejects_generic_csv(tmp_path):
    """is_matrix returns False for a plain date/vendor/amount CSV."""
    f = _write(tmp_path, "generic.csv", _GENERIC_CSV)
    assert is_matrix(f) is False


# ---------------------------------------------------------------------------
# load_matrix record count
# ---------------------------------------------------------------------------

def test_load_matrix_record_count(tmp_path):
    """load_matrix emits one record per (non-skip category) x (non-blank month cell)."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)

    # Revenue: 12, Pet fees: 12, Parents/Friends Stay: 3 (feb, may, sept)
    # 9 expense categories, each 12 months = 108
    # Owner Exp (extra): only 4 filled months (feb, may, aug, nov) = 4 expense rows
    # Total income rows = 12 + 12 + 3 = 27
    # Total expense rows = (8 * 12) + 4 = 100
    # Grand total = 127
    assert len(records) == 127


def test_load_matrix_skip_rows_excluded(tmp_path):
    """Skip rows (Net to owner, Notes, Total, Avg, Months) produce no records."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    sources = {r["vendor"] for r in records}
    skip_labels = {"Net to owner", "Notes", "Total", "Avg Total Proceeds/Month", "Months"}
    assert not (sources & skip_labels)


# ---------------------------------------------------------------------------
# Direction classification
# ---------------------------------------------------------------------------

def test_revenue_is_income(tmp_path):
    """Revenue category rows are classified as income."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    revenue = [r for r in records if r["vendor"] == "Revenue"]
    assert len(revenue) == 12
    assert all(r["direction"] == "income" for r in revenue)


def test_sdge_is_expense(tmp_path):
    """Electricity+ Gas (SDGE) rows are classified as expense."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    sdge = [r for r in records if r["vendor"] == "Electricity+ Gas (SDGE)"]
    assert len(sdge) == 12
    assert all(r["direction"] == "expense" for r in sdge)


# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

def test_dollar_and_comma_stripped(tmp_path):
    """$1,234.56 parses to 1234.56."""
    csv_content = textwrap.dedent("""\
        ,jan,feb
        Revenue,"$1,234.56",
        Mgmt Fees,"$100.00",
    """)
    f = _write(tmp_path, "test.csv", csv_content)
    records = load_matrix(f, 2025, ["Revenue"], ["Mgmt Fees"], [])
    rev = next(r for r in records if r["vendor"] == "Revenue")
    assert rev["amount"] == pytest.approx(1234.56)


def test_paren_amount_stored_as_positive_with_abs(tmp_path):
    """(123.45) in the matrix is parsed as -123.45 then abs -> stored 123.45."""
    csv_content = textwrap.dedent("""\
        ,jan,feb
        Revenue,(500.00),$100.00
        Mgmt Fees,$50.00,
    """)
    f = _write(tmp_path, "test.csv", csv_content)
    records = load_matrix(f, 2025, ["Revenue"], ["Mgmt Fees"], [])
    jan_rev = next(r for r in records if r["vendor"] == "Revenue" and r["date"].endswith("-01-31"))
    assert jan_rev["amount"] == pytest.approx(500.0)
    assert jan_rev["direction"] == "income"


def test_blank_cells_produce_no_records(tmp_path):
    """Blank and '-' cells produce no records (sparse matrix support)."""
    csv_content = textwrap.dedent("""\
        ,jan,feb,march
        Parents/Friends Stay,,-,$200
    """)
    f = _write(tmp_path, "test.csv", csv_content)
    records = load_matrix(f, 2025, ["Parents/Friends Stay"], [], [])
    assert len(records) == 1  # only march
    assert records[0]["amount"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# Column slicing: Total and projection columns ignored
# ---------------------------------------------------------------------------

def test_total_column_ignored(tmp_path):
    """Total column value is not emitted as a record."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    # Revenue total cell in the CSV is $38200 — if Total col were ingested,
    # one record would have amount 38200; verify that is absent.
    amounts = {r["amount"] for r in records if r["vendor"] == "Revenue"}
    assert 38200.0 not in amounts


def test_projection_columns_ignored(tmp_path):
    """Projected Summer Low / Projected Winter Low columns produce no records."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    # Projection columns are blank in our fixture, so this is a shape-completeness check.
    assert all(r["source"] == "cashflow" for r in records)


# ---------------------------------------------------------------------------
# Date: last day of the month
# ---------------------------------------------------------------------------

def test_january_date_is_last_day(tmp_path):
    """January records have date 2025-01-31."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    jan_revs = [r for r in records if r["vendor"] == "Revenue" and r["date"] == "2025-01-31"]
    assert len(jan_revs) == 1


def test_february_date_is_last_day(tmp_path):
    """February 2025 records have date 2025-02-28 (non-leap year)."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    feb_revs = [r for r in records if r["vendor"] == "Revenue" and r["date"] == "2025-02-28"]
    assert len(feb_revs) == 1


# ---------------------------------------------------------------------------
# Year inference from filename
# ---------------------------------------------------------------------------

def test_year_inference_from_two_digit_suffix(tmp_path):
    """Filename 'str_pnl_25.csv' -> year 2025."""
    csv_content = textwrap.dedent("""\
        ,jan
        Revenue,$1000
        Mgmt Fees,$100
    """)
    f = _write(tmp_path, "str_pnl_25.csv", csv_content)
    records = load_matrix(f, None, ["Revenue"], ["Mgmt Fees"], [])
    assert all(r["date"].startswith("2025") for r in records)


def test_year_inference_from_four_digit_stem(tmp_path):
    """Filename 'str_2024.csv' -> year 2024."""
    csv_content = textwrap.dedent("""\
        ,jan
        Revenue,$1000
    """)
    f = _write(tmp_path, "str_2024.csv", csv_content)
    records = load_matrix(f, None, ["Revenue"], [], [])
    assert all(r["date"].startswith("2024") for r in records)


def test_explicit_year_overrides_filename(tmp_path):
    """Explicit year=2023 takes priority over filename digits."""
    csv_content = textwrap.dedent("""\
        ,jan
        Revenue,$1000
    """)
    f = _write(tmp_path, "str_pnl_25.csv", csv_content)
    records = load_matrix(f, 2023, ["Revenue"], [], [])
    assert all(r["date"].startswith("2023") for r in records)


# ---------------------------------------------------------------------------
# Source field
# ---------------------------------------------------------------------------

def test_source_field_is_cashflow(tmp_path):
    """source field is 'cashflow' for all matrix records."""
    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    assert all(r["source"] == "cashflow" for r in records)


# ---------------------------------------------------------------------------
# Case-insensitive + whitespace-tolerant category matching
# ---------------------------------------------------------------------------

def test_category_match_case_insensitive(tmp_path):
    """Category matching is case-insensitive (Nov vs nov in header, Revenue vs revenue in row)."""
    csv_content = textwrap.dedent("""\
        ,JAN,FEB
        REVENUE,$500,$600
        MGMT FEES,$50,$60
    """)
    f = _write(tmp_path, "test.csv", csv_content)
    records = load_matrix(f, 2025, ["Revenue"], ["Mgmt Fees"], [])
    assert len(records) == 4
    rev = [r for r in records if r["direction"] == "income"]
    assert len(rev) == 2


def test_category_match_extra_whitespace(tmp_path):
    """Category matching tolerates extra internal whitespace ('Yard care X2 a  month')."""
    csv_content = textwrap.dedent("""\
        ,jan
        Yard care X2 a  month,$80
    """)
    f = _write(tmp_path, "test.csv", csv_content)
    records = load_matrix(f, 2025, [], ["Yard care X2 a  month"], [])
    assert len(records) == 1
    assert records[0]["direction"] == "expense"


# ---------------------------------------------------------------------------
# include-glob in loader avoids double-counting
# ---------------------------------------------------------------------------

def test_include_glob_filters_to_matrix_only(tmp_path):
    """When ingestion.include is set, loader ingests only matching files."""
    from agent.tenancy import Tenant
    from ingestion.loader import load_transactions

    matrix_f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    chase_f = _write(tmp_path, "chase.csv", _CHASE_HEADER_CSV)

    t = Tenant(
        slug="t",
        data_root=str(tmp_path),
        llm_routing="local",
        sensitivity="restricted",
        mode="advisory",
        ingestion={"include": ["str_pnl_*.csv"]},
    )
    txns = load_transactions(t)
    # All records should come from the matrix (source="cashflow"), not Chase
    assert all(tx["source"] == "cashflow" for tx in txns)
    assert len(txns) == 127


def test_include_glob_empty_means_all_files(tmp_path):
    """When ingestion.include is absent, all files are ingested."""
    from agent.tenancy import Tenant
    from ingestion.loader import load_transactions

    _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    _write(tmp_path, "chase.csv", _CHASE_HEADER_CSV)

    t = Tenant(
        slug="t",
        data_root=str(tmp_path),
        llm_routing="local",
        sensitivity="restricted",
        mode="advisory",
    )
    txns = load_transactions(t)
    sources = {tx["source"] for tx in txns}
    assert "cashflow" in sources
    assert any("chase" in s for s in sources)


# ---------------------------------------------------------------------------
# Integration: compute_pnl + find on melted matrix records
# ---------------------------------------------------------------------------

def test_compute_pnl_on_matrix_records(tmp_path):
    """compute_pnl produces positive net for the synthetic STR fixture."""
    from analysis.pnl import compute_pnl

    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    pnl = compute_pnl(records)

    assert pnl["totals"]["income"] > 0
    assert pnl["totals"]["expense"] > 0
    assert pnl["totals"]["net"] > 0  # synthetic STR is profitable
    assert len(pnl["monthly"]) == 12  # all 12 months present


def test_pnl_january_income(tmp_path):
    """January income = Revenue(2800) + Pet fees(150) = 2950."""
    from analysis.pnl import compute_pnl

    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    pnl = compute_pnl(records)
    assert pnl["monthly"]["2025-01"]["income"] == pytest.approx(2950.0)


def test_pnl_january_expense(tmp_path):
    """January expense = sum of all 8 expense categories with January values."""
    from analysis.pnl import compute_pnl

    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    pnl = compute_pnl(records)
    # 280+80+45+62+35+80+210+45 = 837
    assert pnl["monthly"]["2025-01"]["expense"] == pytest.approx(837.0)


def test_findings_run_on_matrix_records(tmp_path):
    """find() runs without error on melted matrix records and returns a list."""
    from analysis.findings import find
    from gbrain.knowledge_graph import KnowledgeGraph

    f = _write(tmp_path, "str_pnl_25.csv", _MATRIX_CSV)
    records = load_matrix(f, 2025, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP)
    graph = KnowledgeGraph()
    thresholds = {"alert_delta_pct": 20.0, "anomaly_z_score": 2.0}
    findings = find(records, graph, thresholds)
    assert isinstance(findings, list)
