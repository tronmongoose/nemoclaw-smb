"""test_tenant_dashboard.py — Offline tests for analysis/export.py and GET /tenant/{slug}/analysis.

Covers:
- write_analysis_json produces the documented schema from synthetic pnl + findings.
- GET /tenant/_sample_str/analysis returns 200 + schema-valid body when analysis.json exists.
- GET /tenant/_sample_str/analysis returns 404 when analysis.json is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from analysis.export import write_analysis_json
from analysis.pnl import compute_pnl
from agent.tenancy import Tenant


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

def _make_tenant(tmp_path: Path) -> Tenant:
    """Return a synthetic Tenant whose data_root is inside tmp_path."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    return Tenant(
        slug="_sample_str",
        data_root=str(data_root),
        llm_routing="local",
        sensitivity="restricted",
        mode="advisory",
    )


def _make_transactions() -> list[dict]:
    return [
        {"date": "2025-01-10", "vendor": "Acme Rentals", "amount": 3000.0,
         "direction": "income", "category": "rental_income"},
        {"date": "2025-02-10", "vendor": "Acme Rentals", "amount": 3200.0,
         "direction": "income", "category": "rental_income"},
        {"date": "2025-01-05", "vendor": "Power Co", "amount": 120.0,
         "direction": "expense", "category": "utilities"},
        {"date": "2025-02-05", "vendor": "Power Co", "amount": 125.0,
         "direction": "expense", "category": "utilities"},
    ]


def _synthetic_finding() -> "object":
    """Return a minimal Finding-like object with required attrs."""
    from analysis.findings import Finding
    return Finding(
        title="Test spike: Power Co",
        category="utilities",
        monthly_impact=50.0,
        annual_impact=600.0,
        confidence="medium",
        why="Power Co charged $125 vs baseline $120.",
    )


# ---------------------------------------------------------------------------
# write_analysis_json schema tests
# ---------------------------------------------------------------------------

class TestWriteAnalysisJson:
    def test_file_created(self, tmp_path):
        """write_analysis_json creates analysis.json in data_root."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [_synthetic_finding()], "2025-03-01T00:00:00+00:00")
        assert (Path(tenant.data_root) / "analysis.json").exists()

    def test_top_level_keys(self, tmp_path):
        """Schema has required top-level keys: tenant, generated_at, pnl, findings."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for key in ("tenant", "generated_at", "pnl", "findings"):
            assert key in doc, f"Missing top-level key: {key}"

    def test_pnl_totals_keys(self, tmp_path):
        """pnl.totals has income, expense, net, margin_pct."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        totals = doc["pnl"]["totals"]
        for key in ("income", "expense", "net", "margin_pct"):
            assert key in totals

    def test_pnl_by_month_shape(self, tmp_path):
        """pnl.by_month is a list with month/income/expense/net per entry."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        by_month = doc["pnl"]["by_month"]
        assert len(by_month) == 2  # Jan + Feb
        for entry in by_month:
            for key in ("month", "income", "expense", "net"):
                assert key in entry

    def test_pnl_expense_by_category_shape(self, tmp_path):
        """pnl.expense_by_category is a list of {category, amount}."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        cats = doc["pnl"]["expense_by_category"]
        assert len(cats) >= 1
        for entry in cats:
            assert "category" in entry
            assert "amount" in entry

    def test_findings_serialized(self, tmp_path):
        """Findings are serialized with all required fields."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [_synthetic_finding()], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        assert len(doc["findings"]) == 1
        f = doc["findings"][0]
        for key in ("title", "category", "monthly_impact", "annual_impact", "confidence", "why"):
            assert key in f

    def test_margin_pct_zero_income(self, tmp_path):
        """margin_pct is 0.0 when income is zero (no divide-by-zero crash)."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl([])
        write_analysis_json(tenant, pnl, [], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        assert doc["pnl"]["totals"]["margin_pct"] == pytest.approx(0.0)

    def test_margin_pct_correct(self, tmp_path):
        """margin_pct = net / income * 100."""
        tenant = _make_tenant(tmp_path)
        pnl = compute_pnl(_make_transactions())
        write_analysis_json(tenant, pnl, [], "2025-03-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        t = doc["pnl"]["totals"]
        expected = t["net"] / t["income"] * 100
        assert t["margin_pct"] == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# GET /tenant/{slug}/analysis API tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_with_analysis(tmp_path, monkeypatch):
    """TestClient with a synthetic analysis.json in the _sample_str data_root."""
    tenant = _make_tenant(tmp_path)
    pnl = compute_pnl(_make_transactions())
    write_analysis_json(tenant, pnl, [_synthetic_finding()], "2025-03-01T00:00:00+00:00")

    # Patch the name in the route module (imported at module load time)
    import api.routes.tenant as route_mod
    monkeypatch.setattr(route_mod, "load_tenant", lambda slug, tenants_root=None: tenant)

    from api.main import app
    return TestClient(app)


@pytest.fixture()
def client_without_analysis(tmp_path, monkeypatch):
    """TestClient with a tenant whose data_root has NO analysis.json."""
    tenant = _make_tenant(tmp_path)

    import api.routes.tenant as route_mod
    monkeypatch.setattr(route_mod, "load_tenant", lambda slug, tenants_root=None: tenant)

    from api.main import app
    return TestClient(app)


def test_analysis_endpoint_200(client_with_analysis):
    """GET /tenant/_sample_str/analysis returns 200 when analysis.json exists."""
    resp = client_with_analysis.get("/tenant/_sample_str/analysis")
    assert resp.status_code == 200


def test_analysis_endpoint_schema(client_with_analysis):
    """GET /tenant/_sample_str/analysis body has all required top-level schema keys."""
    resp = client_with_analysis.get("/tenant/_sample_str/analysis")
    body = resp.json()
    for key in ("tenant", "generated_at", "pnl", "findings"):
        assert key in body, f"Missing key: {key}"


def test_analysis_endpoint_pnl_totals(client_with_analysis):
    """pnl.totals in the endpoint response has income, expense, net, margin_pct."""
    resp = client_with_analysis.get("/tenant/_sample_str/analysis")
    totals = resp.json()["pnl"]["totals"]
    for key in ("income", "expense", "net", "margin_pct"):
        assert key in totals


def test_analysis_endpoint_404_when_absent(client_without_analysis):
    """GET /tenant/_sample_str/analysis returns 404 when analysis.json is missing."""
    resp = client_without_analysis.get("/tenant/_sample_str/analysis")
    assert resp.status_code == 404
