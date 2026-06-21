"""tests/test_str_api.py: HTTP surface tests for the three STR acts.

Drives api.main.app via FastAPI TestClient and asserts each endpoint returns
200 (or the documented 402) plus the documented body shape:

    Act I  : /str/act1/{property_id}/{month} -> anomaly + provenance
    Act II : checkout / payouts / invoices / portfolio
    Act III: price / aeo-audit (real 402-then-200) / metrics
    Audit  : /str/audit -> STR-scoped entries + verify ok
    Mount  : payments/mpp_server.app mounted at /mpp

All tests run with DEMO_MODE=true and live=false (default), so no network or
credentials are touched. The audit env path is pinned to the shared demo chain
so Act payments, earn events, and verify_chain all read one coherent log.
"""
from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
# Pin the env-default audit path to the demo chain so Act I/II append_action
# writes and Act III earn events land in the same file /str/audit verifies.
os.environ["NEMOCLAW_AUDIT_PATH"] = "audit/demo_audit.jsonl"

import pytest  # noqa: E402 -- env must be set before app import
from fastapi.testclient import TestClient  # noqa: E402

from acts import platform_agent  # noqa: E402
from api.main import app  # noqa: E402

_VALID_TOKEN = "mpp_tok_demo"

_PRICE_BODY = {
    "property_id": "prop-001",
    "current_rate": 200.0,
    "occupancy_rate": 0.75,
    "local_events": ["Comic-Con International"],
    "comp_set_rates": [195.0, 215.0],
    "season": "peak",
    "day_of_week": "sat",
}

_AEO_BODY = {
    "listing_text": "2BR beach house in Oceanside, CA. Up to 4 guests. Check-in 4pm.",
    "amenities_list": ["wifi", "parking"],
    "existing_schema": {"checkinTime": "16:00"},
    "listing_url": "https://example.com/listing/test",
}


@pytest.fixture()
def client():
    """TestClient for the main app with platform metrics reset per test."""
    platform_agent.reset_metrics()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Act I: reconciliation
# ---------------------------------------------------------------------------


def test_act1_returns_200_and_report_shape(client):
    """GET /str/act1 returns 200 with the full reconciliation report shape."""
    resp = client.get("/str/act1/prop-001/2026-06")
    assert resp.status_code == 200
    body = resp.json()
    assert body["property_id"] == "prop-001"
    assert body["month"] == "2026-06"
    assert "summary" in body
    assert "anomaly" in body
    assert body["audit_ok"] is True


def test_act1_returns_anomaly_and_provenance(client):
    """GET /str/act1 for prop-001 surfaces the anomaly and reasoning provenance."""
    resp = client.get("/str/act1/prop-001/2026-06")
    assert resp.status_code == 200
    anomaly = resp.json()["anomaly"]
    assert anomaly["is_anomaly"] is True
    assert anomaly["overcharge_cents"] > 0
    prov = anomaly["reasoning_provenance"]
    assert prov["mode"] == "demo"
    assert "model" in prov
    assert "latency_ms" in prov
    assert prov["source"] == "cached"


def test_act1_live_param_threads_through(client):
    """live=false (default and explicit) keeps the demo reasoning path offline."""
    resp = client.get("/str/act1/prop-001/2026-06", params={"live": "false"})
    assert resp.status_code == 200
    assert resp.json()["anomaly"]["reasoning_provenance"]["mode"] == "demo"


# ---------------------------------------------------------------------------
# Act II: property-management orchestration
# ---------------------------------------------------------------------------


def test_act2_checkout_returns_card_result(client):
    """POST /str/act2/checkout issues a cleaner card and returns its shape."""
    resp = client.post(
        "/str/act2/checkout",
        json={"property_id": "prop-001", "checkout_date": "2026-06-15"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["property_id"] == "prop-001"
    assert body["card_token"].startswith("tok_")
    assert "7349" in body["mcc_list"]
    assert body["amount_cap_cents"] > 0


def test_act2_payouts_returns_batch(client):
    """GET /str/act2/payouts returns a payout batch with per-member records."""
    resp = client.get("/str/act2/payouts/2026-06")
    assert resp.status_code == 200
    body = resp.json()
    assert body["month"] == "2026-06"
    assert len(body["records"]) == 3
    assert body["total_cents"] > 0


def test_act2_invoices_returns_owner_invoices(client):
    """GET /str/act2/invoices returns one UBP invoice per owner."""
    resp = client.get("/str/act2/invoices/2026-06")
    assert resp.status_code == 200
    body = resp.json()
    assert body["month"] == "2026-06"
    assert len(body["invoices"]) >= 1
    first = body["invoices"][0]
    assert "owner_id" in first
    assert "total_fee_cents" in first
    assert "line_items" in first


def test_act2_portfolio_returns_summary(client):
    """GET /str/act2/portfolio returns the portfolio summary across properties."""
    resp = client.get("/str/act2/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["property_count"] == 5
    assert body["owner_count"] >= 1
    assert len(body["property_ids"]) == 5


# ---------------------------------------------------------------------------
# Act III: platform earn server
# ---------------------------------------------------------------------------


def test_act3_price_returns_recommendation(client):
    """POST /str/act3/price returns 200 with a pricing recommendation + earn event."""
    resp = client.post("/str/act3/price", json=_PRICE_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "price"
    assert body["amount_cents"] == 25
    assert "recommended_rate" in body["recommendation"]
    assert "chain_hash" in body["earn_event"]


def test_act3_aeo_audit_402_without_token(client):
    """POST /str/act3/aeo-audit with no token returns the real 402 + header."""
    resp = client.post("/str/act3/aeo-audit", json=_AEO_BODY)
    assert resp.status_code == 402
    www_auth = resp.headers.get("www-authenticate", "")
    assert "stripe-mpp" in www_auth
    assert "charge=$1.00" in www_auth


def test_act3_aeo_audit_200_with_token(client):
    """POST /str/act3/aeo-audit with an mpp_tok_ token returns 200 + audit result."""
    resp = client.post(
        "/str/act3/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "aeo-audit"
    assert body["amount_cents"] == 100
    assert "overall_score" in body["result"]


def test_act3_metrics_returns_counts(client):
    """GET /str/act3/metrics returns the platform metrics shape after a call."""
    client.post("/str/act3/price", json=_PRICE_BODY)
    resp = client.get("/str/act3/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["calls_served"] >= 1
    assert body["revenue_earned_cents"] >= 25
    assert "properties_optimized" in body


# ---------------------------------------------------------------------------
# STR-scoped audit + chain verification
# ---------------------------------------------------------------------------


def test_str_audit_returns_entries_and_verify_ok(client):
    """GET /str/audit returns STR-scoped entries and a passing verify_chain."""
    # Generate at least one STR audit entry (earn event) first.
    client.post(
        "/str/act3/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    resp = client.get("/str/audit", params={"limit": 50})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verify"]["ok"] is True
    assert body["count"] >= 1
    assert isinstance(body["entries"], list)


# ---------------------------------------------------------------------------
# MPP server folded in under /mpp
# ---------------------------------------------------------------------------


def test_mpp_mount_402_without_token(client):
    """The mounted MPP server returns 402 on /mpp/aeo-audit without a token."""
    resp = client.post("/mpp/aeo-audit", json=_AEO_BODY)
    assert resp.status_code == 402


def test_mpp_mount_200_with_token(client):
    """The mounted MPP server returns 200 on /mpp/price with a valid token."""
    resp = client.post(
        "/mpp/price",
        json=_PRICE_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    assert resp.json()["service"] == "price"
