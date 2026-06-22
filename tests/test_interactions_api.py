"""HTTP tests for GET /str/interactions (seeded historical feed + filters)."""
from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ["NEMOCLAW_AUDIT_PATH"] = "audit/demo_audit.jsonl"

import pytest  # noqa: E402 (env must be set before app import)
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.seed import reset_demo, seed_demo, DEMO_INTERACTIONS_PATH  # noqa: E402
from agent.interactions_log import append_interaction  # noqa: E402

# The canned demo seed was removed (the live feed fills from real calls), so the endpoint
# tests append a representative, real-shaped set themselves.
_FIXTURE_INTERACTIONS = [
    ("NVIDIA", "anomaly reasoning", "owner", "ok", "nvidia/nemotron-3-super-120b-a12b", 1800.0, "live", {}),
    ("Stripe", "reconciliation payout", "owner", "ok", None, None, None, {"amount_cents": 8400}),
    ("C1", "authorize NHI", "owner", "ok", None, 2.6, None, {"source": "baton-carryall"}),
    ("Stripe", "card issue (Issuing for Agents)", "firm", "ok", None, None, None, {"amount_cents": 7500}),
    ("Stripe", "crew payout (Connect + Global Payouts)", "firm", "ok", None, None, None, {"amount_cents": 42000}),
    ("C1", "authorize NHI (scoped cleaner)", "firm", "ok", None, 3.1, None, {"source": "baton-carryall"}),
    ("Nous Research", "guest comms (Sales)", "agent", "ok", "nousresearch/hermes-4-70b", 1700.0, "live", {"amount_cents": 150}),
    ("NVIDIA", "dynamic pricing", "agent", "ok", "nvidia/nemotron-3-super-120b-a12b", 1850.0, "live", {}),
    ("Stripe", "MPP earn: guest-comms", "agent", "ok", None, None, None, {"amount_cents": 150}),
]


@pytest.fixture(autouse=True)
def _seeded():
    reset_demo()
    seed_demo()
    for sponsor, op, segment, status, model, latency, mode, meta in _FIXTURE_INTERACTIONS:
        append_interaction(
            sponsor=sponsor, op=op, segment=segment, status=status,
            model=model, latency_ms=latency, mode=mode, metadata=meta,
            path=DEMO_INTERACTIONS_PATH,
        )
    yield


def test_interactions_shape():
    c = TestClient(app)
    r = c.get("/str/interactions?limit=50")
    assert r.status_code == 200
    body = r.json()
    assert body["verify"]["ok"] is True
    assert body["count"] >= 1
    entry = body["entries"][0]
    for key in ("sponsor", "op", "segment", "status"):
        assert key in entry


def test_interactions_segment_filter():
    c = TestClient(app)
    r = c.get("/str/interactions?segment=firm")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert entries, "expected seeded firm interactions"
    assert all(e["segment"] == "firm" for e in entries)


def test_interactions_sponsor_filter():
    c = TestClient(app)
    r = c.get("/str/interactions?sponsor=Stripe")
    assert r.status_code == 200
    assert all(e["sponsor"] == "Stripe" for e in r.json()["entries"])


def test_interactions_covers_three_sponsors():
    c = TestClient(app)
    entries = c.get("/str/interactions?limit=100").json()["entries"]
    sponsors = {e["sponsor"] for e in entries}
    assert {"NVIDIA", "Stripe", "Nous Research"}.issubset(sponsors)
