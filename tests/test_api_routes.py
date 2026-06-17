"""Tests for FastAPI routes via TestClient.

Covers: GET /health, GET /graph keys, POST /webhooks/402 paid outcome,
POST /webhooks/stripe missing signature -> 400, GET /approvals/pending list.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_stripe_secret(monkeypatch):
    """Ensure STRIPE_WEBHOOK_SECRET is unset so demo mode is active."""
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)


@pytest.fixture(autouse=True)
def _clear_approvals_dir(tmp_path, monkeypatch):
    """Redirect approval state to a per-test temp dir."""
    d = tmp_path / "approvals"
    d.mkdir()
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(d))


@pytest.fixture()
def client():
    """Return a TestClient for the nemoclaw-smb FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_200(client):
    """Health probe must return HTTP 200."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_returns_ok_status(client):
    """Health probe body must contain status=ok."""
    resp = client.get("/health")
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /graph
# ---------------------------------------------------------------------------

def test_graph_returns_200(client):
    """GET /graph must return HTTP 200."""
    resp = client.get("/graph")
    assert resp.status_code == 200


def test_graph_has_nodes_and_edges_keys(client):
    """GET /graph body must contain 'nodes' and 'edges' keys."""
    resp = client.get("/graph")
    body = resp.json()
    assert "nodes" in body
    assert "edges" in body


# ---------------------------------------------------------------------------
# POST /webhooks/402 — paid outcome
# ---------------------------------------------------------------------------

def test_webhook_402_paid_outcome(client, monkeypatch):
    """An in-range AWS renewal event must resolve to outcome=paid."""
    monkeypatch.delenv("C1_API_KEY", raising=False)
    payload = {
        "vendor": "AWS",
        "amount": 312.0,
        "date": "2026-06-15",
        "invoice_id": "INV-TEST-001",
        "trigger": "http_402",
    }
    resp = client.post("/webhooks/402", json=payload)
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "paid"


# ---------------------------------------------------------------------------
# POST /webhooks/stripe — missing signature -> 400
# ---------------------------------------------------------------------------

def test_webhook_stripe_missing_signature_returns_400(client):
    """Stripe webhook without Stripe-Signature header must return 400."""
    resp = client.post("/webhooks/stripe", content=b"{}")
    assert resp.status_code == 400


def test_webhook_stripe_with_signature_returns_200(client):
    """Stripe webhook with Stripe-Signature header must return 200 in demo mode."""
    resp = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "t=1,v1=abc123"},
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


# ---------------------------------------------------------------------------
# GET /approvals/pending
# ---------------------------------------------------------------------------

def test_approvals_pending_returns_list(client):
    """GET /approvals/pending must return a JSON list."""
    resp = client.get("/approvals/pending")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
