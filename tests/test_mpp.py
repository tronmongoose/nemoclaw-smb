"""tests/test_mpp.py -- MPP server and earn-layer tests for Act 3.

Verifies:
    - /price returns 402 + correct WWW-Authenticate header when no token
    - /aeo-audit returns 402 + correct WWW-Authenticate header when no token
    - valid token (mpp_tok_*) unlocks execution (200 + body)
    - earn event is written to audit chain after successful call
    - earn amounts correct (25c pricing, 100c AEO)

All tests pass DEMO_MODE=true with no credentials.
"""
from __future__ import annotations

import json
import os
import tempfile

os.environ.setdefault("DEMO_MODE", "true")

import pytest
from fastapi.testclient import TestClient

from payments.mpp_server import (
    AEO_AUDIT_ENDPOINT_CENTS,
    PRICE_ENDPOINT_CENTS,
    app,
    validate_mpp_token,
)
from agent.audit_log import verify_chain

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """TestClient with NEMOCLAW_AUDIT_PATH pointed to a fresh tmp file."""
    audit_file = str(tmp_path / "audit.jsonl")
    os.environ["NEMOCLAW_AUDIT_PATH"] = audit_file
    yield TestClient(app)
    # Cleanup env so sibling tests don't share the tmp file
    os.environ.pop("NEMOCLAW_AUDIT_PATH", None)


_VALID_TOKEN = "mpp_tok_test1234"
_INVALID_TOKEN = "bad_token_not_valid"

_PRICE_BODY: dict = {
    "property_id": "prop-001",
    "current_rate": 200.0,
    "occupancy_rate": 0.75,
    "local_events": ["Comic-Con International"],
    "comp_set_rates": [195.0, 215.0],
    "season": "peak",
    "day_of_week": "sat",
}

_AEO_BODY: dict = {
    "listing_text": "2BR beach house in Oceanside, CA. Up to 4 guests. Check-in 4pm.",
    "amenities_list": ["wifi", "parking"],
    "existing_schema": {"checkinTime": "16:00"},
    "listing_url": "https://example.com/listing/test",
}

# ---------------------------------------------------------------------------
# 402 behavior -- no token
# ---------------------------------------------------------------------------

def test_price_returns_402_without_token(client):
    """POST /price with no Authorization header returns 402."""
    resp = client.post("/price", json=_PRICE_BODY)
    assert resp.status_code == 402


def test_price_402_www_authenticate_header(client):
    """POST /price 402 response carries the correct Stripe-MPP WWW-Authenticate header."""
    resp = client.post("/price", json=_PRICE_BODY)
    assert resp.status_code == 402
    www_auth = resp.headers.get("www-authenticate", "")
    assert "stripe-mpp" in www_auth
    assert "charge=$0.25" in www_auth
    assert "currency=usd" in www_auth


def test_aeo_returns_402_without_token(client):
    """POST /aeo-audit with no Authorization header returns 402."""
    resp = client.post("/aeo-audit", json=_AEO_BODY)
    assert resp.status_code == 402


def test_aeo_402_www_authenticate_header(client):
    """POST /aeo-audit 402 response carries the correct Stripe-MPP WWW-Authenticate header."""
    resp = client.post("/aeo-audit", json=_AEO_BODY)
    assert resp.status_code == 402
    www_auth = resp.headers.get("www-authenticate", "")
    assert "stripe-mpp" in www_auth
    assert "charge=$1.00" in www_auth
    assert "currency=usd" in www_auth


def test_price_402_with_invalid_token(client):
    """POST /price with an invalid token returns 402."""
    resp = client.post(
        "/price",
        json=_PRICE_BODY,
        headers={"Authorization": f"Bearer {_INVALID_TOKEN}"},
    )
    assert resp.status_code == 402


def test_aeo_402_with_invalid_token(client):
    """POST /aeo-audit with an invalid token returns 402."""
    resp = client.post(
        "/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_INVALID_TOKEN}"},
    )
    assert resp.status_code == 402


# ---------------------------------------------------------------------------
# Valid token unlocks execution
# ---------------------------------------------------------------------------

def test_price_200_with_valid_token(client):
    """POST /price with a valid mpp_tok_ token returns 200 and a recommendation."""
    resp = client.post(
        "/price",
        json=_PRICE_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "price"
    assert "result" in body
    assert "recommended_rate" in body["result"]
    assert "confidence" in body["result"]


def test_aeo_200_with_valid_token(client):
    """POST /aeo-audit with a valid token returns 200 and an audit result."""
    resp = client.post(
        "/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "aeo-audit"
    assert "result" in body
    assert "overall_score" in body["result"]


# ---------------------------------------------------------------------------
# Earn amounts correct
# ---------------------------------------------------------------------------

def test_price_earn_amount_is_25_cents(client):
    """Successful /price call reports 25 cents earned."""
    resp = client.post(
        "/price",
        json=_PRICE_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    assert resp.json()["amount_cents"] == PRICE_ENDPOINT_CENTS
    assert resp.json()["amount_cents"] == 25


def test_aeo_earn_amount_is_100_cents(client):
    """Successful /aeo-audit call reports 100 cents earned."""
    resp = client.post(
        "/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    assert resp.json()["amount_cents"] == AEO_AUDIT_ENDPOINT_CENTS
    assert resp.json()["amount_cents"] == 100


# ---------------------------------------------------------------------------
# Earn event written to audit chain
# ---------------------------------------------------------------------------

def test_price_earn_event_written_to_audit_chain(client, tmp_path):
    """Successful /price call writes an mpp_earn event to the audit chain."""
    audit_file = os.environ["NEMOCLAW_AUDIT_PATH"]

    resp = client.post(
        "/price",
        json=_PRICE_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200

    entries = _read_audit_entries(audit_file)
    assert len(entries) >= 1
    earn = _find_earn_event(entries, "price")
    assert earn is not None
    assert earn["event"] == "mpp_earn"
    assert earn["service"] == "price"
    assert earn["amount_cents"] == 25
    assert earn["token_id"] == _VALID_TOKEN
    assert "entry_hash" in earn


def test_aeo_earn_event_written_to_audit_chain(client, tmp_path):
    """Successful /aeo-audit call writes an mpp_earn event to the audit chain."""
    audit_file = os.environ["NEMOCLAW_AUDIT_PATH"]

    resp = client.post(
        "/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    assert resp.status_code == 200

    entries = _read_audit_entries(audit_file)
    assert len(entries) >= 1
    earn = _find_earn_event(entries, "aeo-audit")
    assert earn is not None
    assert earn["event"] == "mpp_earn"
    assert earn["service"] == "aeo-audit"
    assert earn["amount_cents"] == 100
    assert earn["token_id"] == _VALID_TOKEN
    assert "entry_hash" in earn


def test_audit_chain_integrity_after_earn(client):
    """Hash chain is valid after one or more earn events."""
    audit_file = os.environ["NEMOCLAW_AUDIT_PATH"]

    client.post(
        "/price",
        json=_PRICE_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )
    client.post(
        "/aeo-audit",
        json=_AEO_BODY,
        headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
    )

    ok, msg = verify_chain(audit_file)
    assert ok, f"Audit chain integrity failed: {msg}"


# ---------------------------------------------------------------------------
# Token validation unit tests
# ---------------------------------------------------------------------------

def test_valid_demo_token_accepted():
    """mpp_tok_ prefix tokens are valid in DEMO_MODE."""
    assert validate_mpp_token("mpp_tok_abc123") is True


def test_invalid_token_rejected():
    """Tokens without the mpp_tok_ prefix are rejected in DEMO_MODE."""
    assert validate_mpp_token("stripe_tok_abc") is False
    assert validate_mpp_token("") is False
    assert validate_mpp_token("mpp_") is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_audit_entries(audit_file: str) -> list[dict]:
    """Read all JSONL lines from the audit file."""
    path_obj = __import__("pathlib").Path(audit_file)
    if not path_obj.exists():
        return []
    lines = [line.strip() for line in path_obj.read_text().splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def _find_earn_event(entries: list[dict], service: str) -> dict | None:
    """Return the first mpp_earn entry matching service, or None."""
    for entry in entries:
        if entry.get("event") == "mpp_earn" and entry.get("service") == service:
            return entry
    return None
