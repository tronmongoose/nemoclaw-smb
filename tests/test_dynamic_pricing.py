"""tests/test_dynamic_pricing.py: dynamic pricing skill live-vs-demo toggle.

Covers the live reasoning param and provenance shape on recommend_price.
All tests pass with DEMO_MODE=true and no live API credentials.
"""
from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")

from skills.dynamic_pricing_skill import PricingRequest, recommend_price


def _req() -> PricingRequest:
    """Build a representative peak-weekend PricingRequest."""
    return PricingRequest(
        property_id="prop-001",
        current_rate=200.0,
        occupancy_rate=0.82,
        local_events=["Comic-Con International"],
        comp_set_rates=[195.0, 230.0, 265.0],
        season="peak",
        day_of_week="sat",
    )


def test_recommend_price_accepts_live_param_default_demo() -> None:
    """recommend_price accepts a live param; default keeps demo provenance."""
    rec = recommend_price(_req())  # live defaults False
    assert rec.reasoning_provenance["mode"] == "demo"
    assert rec.reasoning_provenance["source"] == "cached"
    assert rec.recommended_rate > 0


def test_provenance_shape() -> None:
    """reasoning_provenance must carry mode, model, latency_ms, source keys."""
    rec = recommend_price(_req())
    prov = rec.reasoning_provenance
    assert set(prov.keys()) == {"mode", "model", "latency_ms", "source"}
    assert isinstance(prov["latency_ms"], float)
    assert isinstance(prov["model"], str) and prov["model"]


def test_live_true_calls_nemotron(monkeypatch) -> None:
    """live=True with a key present must call call_nemotron; source=nemotron."""
    import skills.dynamic_pricing_skill as m
    called = {"n": 0}

    def fake_call(prompt, **kwargs):
        called["n"] += 1
        return "live nemotron pricing rationale"

    monkeypatch.setattr(m, "nemotron_available", lambda: True)
    monkeypatch.setattr(m, "call_nemotron", fake_call)

    rec = recommend_price(_req(), live=True)

    assert called["n"] == 1, "call_nemotron must be invoked when live=True"
    assert rec.reasoning_provenance["mode"] == "live"
    assert rec.reasoning_provenance["source"] == "nemotron"
    assert rec.reasoning_provenance["latency_ms"] >= 0.0
    assert rec.reasoning == "live nemotron pricing rationale"


def test_live_false_does_not_call_nemotron(monkeypatch) -> None:
    """live=False must NOT call call_nemotron even when a key is present."""
    import skills.dynamic_pricing_skill as m
    called = {"n": 0}

    def fake_call(prompt, **kwargs):
        called["n"] += 1
        return "should not appear"

    monkeypatch.setattr(m, "nemotron_available", lambda: True)
    monkeypatch.setattr(m, "call_nemotron", fake_call)

    rec = recommend_price(_req(), live=False)

    assert called["n"] == 0, "call_nemotron must NOT be invoked when live=False"
    assert rec.reasoning_provenance["mode"] == "demo"
    assert rec.reasoning_provenance["source"] == "cached"


def test_live_true_no_key_falls_back_to_demo(monkeypatch) -> None:
    """live=True with NO key must skip the call and keep demo provenance."""
    import skills.dynamic_pricing_skill as m
    called = {"n": 0}

    def fake_call(prompt, **kwargs):
        called["n"] += 1
        return "should not appear"

    monkeypatch.setattr(m, "nemotron_available", lambda: False)
    monkeypatch.setattr(m, "call_nemotron", fake_call)

    rec = recommend_price(_req(), live=True)

    assert called["n"] == 0, "no key means no live call"
    assert rec.reasoning_provenance["mode"] == "demo"
    assert rec.reasoning_provenance["source"] == "cached"
