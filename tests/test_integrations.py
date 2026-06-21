"""Tests for GET /integrations/status and GET /integrations/verify.

Offline only: no live nemotron/hermes network calls. Stripe probe is
offline-safe in DEMO mode. The conductorone verify call exercises authorize()
locally against the bundled c1z fixture or synthetic fallback.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestIntegrationsStatus:
    """GET /integrations/status contract checks."""

    def test_returns_200(self):
        resp = client.get("/integrations/status")
        assert resp.status_code == 200

    def test_agent_kind_core(self):
        data = client.get("/integrations/status").json()
        assert data["agent"]["kind"] == "core"

    def test_agent_status_real(self):
        data = client.get("/integrations/status").json()
        assert data["agent"]["status"] == "REAL"

    def test_exactly_four_pillars(self):
        data = client.get("/integrations/status").json()
        assert len(data["pillars"]) == 4

    def test_pillar_ids(self):
        data = client.get("/integrations/status").json()
        ids = {p["id"] for p in data["pillars"]}
        assert ids == {"nemotron", "hermes", "stripe", "conductorone"}

    def test_stripe_status_demo(self):
        data = client.get("/integrations/status").json()
        stripe = next(p for p in data["pillars"] if p["id"] == "stripe")
        assert stripe["status"] == "DEMO"

    def test_stripe_skills_contain_issuing_for_agents(self):
        data = client.get("/integrations/status").json()
        stripe = next(p for p in data["pillars"] if p["id"] == "stripe")
        assert "Issuing for Agents" in stripe["skills"]

    def test_stripe_skills_contain_mpp_http402(self):
        data = client.get("/integrations/status").json()
        stripe = next(p for p in data["pillars"] if p["id"] == "stripe")
        assert "MPP / HTTP-402" in stripe["skills"]

    def test_all_nodes_have_required_keys(self):
        data = client.get("/integrations/status").json()
        required = {"id", "kind", "status", "detail"}
        agent = data["agent"]
        assert required.issubset(agent.keys()), f"agent missing keys: {required - agent.keys()}"
        for pillar in data["pillars"]:
            assert required.issubset(pillar.keys()), f"{pillar['id']} missing keys: {required - pillar.keys()}"


class TestIntegrationsVerify:
    """GET /integrations/verify?pillar=<id> contract checks."""

    def test_stripe_returns_200(self):
        resp = client.get("/integrations/verify?pillar=stripe")
        assert resp.status_code == 200

    def test_stripe_response_has_required_keys(self):
        data = client.get("/integrations/verify?pillar=stripe").json()
        assert {"id", "status", "detail", "latency_ms"}.issubset(data.keys())

    def test_stripe_id_is_stripe(self):
        data = client.get("/integrations/verify?pillar=stripe").json()
        assert data["id"] == "stripe"

    def test_stripe_latency_ms_is_numeric(self):
        data = client.get("/integrations/verify?pillar=stripe").json()
        assert isinstance(data["latency_ms"], (int, float))

    def test_unknown_pillar_returns_400(self):
        resp = client.get("/integrations/verify?pillar=unknown_xyz")
        assert resp.status_code == 400

    def test_unknown_pillar_detail_mentions_pillar(self):
        resp = client.get("/integrations/verify?pillar=unknown_xyz")
        body = resp.json()
        assert "unknown_xyz" in body.get("detail", "")
