"""Tests for dashboard read endpoints added in the dashboard iteration.

Covers:
    GET /invoices                 — list, pagination, shape
    GET /invoices/anomalies       — anomaly list, shape
    GET /savings/alternatives     — ranked alternatives, shape
    GET /savings/summary          — summary shape, fee arithmetic
    GET /audit                    — audit chain shape, verify.ok
    GET /approvals/pending        — seeded Adobe escalation present after startup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.seed import reset_demo, seed_demo, DEMO_AUDIT_PATH
from fixtures.seed_data import seed_invoices


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_stripe_secret(monkeypatch):
    """Ensure STRIPE_WEBHOOK_SECRET is unset (demo mode)."""
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)


@pytest.fixture(autouse=True)
def _isolated_approvals(tmp_path, monkeypatch):
    """Redirect approval state to a per-test temp directory."""
    d = tmp_path / "approvals"
    d.mkdir()
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(d))


@pytest.fixture(autouse=True)
def _isolated_audit(tmp_path, monkeypatch):
    """Redirect demo audit writes to a per-test temp file and re-seed."""
    audit_file = tmp_path / "demo_audit.jsonl"
    # Patch the path used by seed.py and audit route at the module level.
    import api.seed as seed_mod
    import api.routes.audit as audit_mod
    original_seed_path = seed_mod.DEMO_AUDIT_PATH
    original_audit_path = audit_mod.DEMO_AUDIT_PATH

    seed_mod.DEMO_AUDIT_PATH = audit_file
    audit_mod.DEMO_AUDIT_PATH = audit_file

    reset_demo()
    seed_demo()

    yield

    seed_mod.DEMO_AUDIT_PATH = original_seed_path
    audit_mod.DEMO_AUDIT_PATH = original_audit_path
    reset_demo()


@pytest.fixture()
def client():
    """TestClient for the nemoclaw-smb app (lifespan skipped; seed_demo called above)."""
    # Use raise_server_exceptions=True (default); lifespan is tested separately.
    return TestClient(app, raise_server_exceptions=True)


# Import app after fixtures so env vars are set first.
from api.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# GET /invoices
# ---------------------------------------------------------------------------

def test_invoices_returns_200(client):
    """GET /invoices returns HTTP 200."""
    resp = client.get("/invoices")
    assert resp.status_code == 200


def test_invoices_returns_list(client):
    """GET /invoices returns a JSON list."""
    resp = client.get("/invoices")
    assert isinstance(resp.json(), list)


def test_invoices_shape(client):
    """Each invoice dict has required keys."""
    resp = client.get("/invoices")
    required = {"invoice_id", "vendor", "description", "amount", "date", "category"}
    for inv in resp.json():
        assert required.issubset(inv.keys()), f"missing keys in {inv}"


def test_invoices_sorted_date_desc(client):
    """Invoices are returned newest-first."""
    resp = client.get("/invoices")
    dates = [inv["date"] for inv in resp.json()]
    assert dates == sorted(dates, reverse=True)


def test_invoices_limit_respected(client):
    """limit query param caps the number of invoices returned."""
    resp = client.get("/invoices?limit=3")
    assert len(resp.json()) == 3


def test_invoices_default_limit(client):
    """Default limit of 50 applies; seed has 21 invoices so all are returned."""
    all_count = len(seed_invoices())
    resp = client.get("/invoices")
    assert len(resp.json()) == all_count


# ---------------------------------------------------------------------------
# GET /invoices/anomalies
# ---------------------------------------------------------------------------

def test_anomalies_returns_200(client):
    """GET /invoices/anomalies returns HTTP 200."""
    resp = client.get("/invoices/anomalies")
    assert resp.status_code == 200


def test_anomalies_returns_list(client):
    """GET /invoices/anomalies returns a JSON list."""
    assert isinstance(client.get("/invoices/anomalies").json(), list)


def test_anomalies_shape(client):
    """Each anomaly dict has the documented fields."""
    required = {
        "vendor", "current_amount", "baseline_mean",
        "z_score", "pct_change", "is_anomaly", "reason",
    }
    for item in client.get("/invoices/anomalies").json():
        assert required.issubset(item.keys()), f"missing keys in {item}"


def test_anomalies_contains_adobe(client):
    """The June Adobe spike must be flagged as an anomaly at default threshold."""
    items = client.get("/invoices/anomalies").json()
    vendors = [i["vendor"] for i in items]
    assert "Adobe Creative Cloud" in vendors


def test_anomalies_all_flagged(client):
    """All returned anomalies have is_anomaly=True (scan filters)."""
    for item in client.get("/invoices/anomalies").json():
        assert item["is_anomaly"] is True


# ---------------------------------------------------------------------------
# GET /savings/alternatives
# ---------------------------------------------------------------------------

def test_alternatives_returns_200(client):
    """GET /savings/alternatives returns HTTP 200."""
    resp = client.get("/savings/alternatives")
    assert resp.status_code == 200


def test_alternatives_shape(client):
    """Response has 'current' and 'ranked' keys."""
    body = client.get("/savings/alternatives").json()
    assert "current" in body
    assert "ranked" in body


def test_alternatives_current_fields(client):
    """'current' dict has vendor and amount."""
    current = client.get("/savings/alternatives").json()["current"]
    assert "vendor" in current
    assert "amount" in current


def test_alternatives_ranked_fields(client):
    """Each ranked alternative has the required keys."""
    ranked = client.get("/savings/alternatives").json()["ranked"]
    required = {"vendor", "amount", "monthly_savings", "annual_savings", "rank"}
    for alt in ranked:
        assert required.issubset(alt.keys()), f"missing keys in {alt}"


def test_alternatives_ranked_by_savings(client):
    """Ranked list is sorted descending by monthly_savings."""
    ranked = client.get("/savings/alternatives").json()["ranked"]
    savings = [r["monthly_savings"] for r in ranked]
    assert savings == sorted(savings, reverse=True)


# ---------------------------------------------------------------------------
# GET /savings/summary
# ---------------------------------------------------------------------------

def test_summary_returns_200(client):
    """GET /savings/summary returns HTTP 200."""
    assert client.get("/savings/summary").status_code == 200


def test_summary_shape(client):
    """Response has expected keys."""
    body = client.get("/savings/summary").json()
    required = {
        "total_spend", "monthly_savings", "annual_savings",
        "nemoclaw_fee", "fee_rate", "currency",
    }
    assert required.issubset(body.keys())


def test_summary_fee_arithmetic(client):
    """nemoclaw_fee == round(total_spend * 0.005, 2)."""
    body = client.get("/savings/summary").json()
    expected_fee = round(body["total_spend"] * 0.005, 2)
    assert body["nemoclaw_fee"] == expected_fee


def test_summary_fee_rate(client):
    """fee_rate is exactly 0.005."""
    assert client.get("/savings/summary").json()["fee_rate"] == 0.005


def test_summary_currency_usd(client):
    """currency field is 'USD'."""
    assert client.get("/savings/summary").json()["currency"] == "USD"


# ---------------------------------------------------------------------------
# GET /audit
# ---------------------------------------------------------------------------

def test_audit_returns_200(client):
    """GET /audit returns HTTP 200."""
    assert client.get("/audit").status_code == 200


def test_audit_shape(client):
    """Response has count, entries, verify keys."""
    body = client.get("/audit").json()
    assert "count" in body
    assert "entries" in body
    assert "verify" in body


def test_audit_verify_ok(client):
    """verify.ok is True on a freshly seeded chain."""
    verify = client.get("/audit").json()["verify"]
    assert verify["ok"] is True


def test_audit_has_entries_after_seed(client):
    """Audit chain has at least one entry after seeding."""
    body = client.get("/audit").json()
    assert body["count"] >= 1
    assert len(body["entries"]) >= 1


def test_audit_limit(client):
    """limit param caps entries returned."""
    resp = client.get("/audit?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["entries"]) <= 1


# ---------------------------------------------------------------------------
# GET /approvals/pending — seeded Adobe escalation
# ---------------------------------------------------------------------------

def test_approvals_pending_has_adobe_after_seed(client):
    """After seeding, /approvals/pending contains the Adobe Creative Cloud escalation."""
    pending = client.get("/approvals/pending").json()
    vendors = [p.get("vendor") for p in pending]
    assert "Adobe Creative Cloud" in vendors, (
        f"Expected 'Adobe Creative Cloud' in pending vendors, got: {vendors}"
    )
