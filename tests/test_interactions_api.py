"""HTTP tests for GET /str/interactions (seeded historical feed + filters)."""
from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ["NEMOCLAW_AUDIT_PATH"] = "audit/demo_audit.jsonl"

import pytest  # noqa: E402 (env must be set before app import)
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.seed import reset_demo, seed_demo  # noqa: E402


@pytest.fixture(autouse=True)
def _seeded():
    reset_demo()
    seed_demo()
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
