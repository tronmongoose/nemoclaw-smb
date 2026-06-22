"""tests/test_guest_comms.py: guest_comms_skill live-vs-demo toggle.

Covers intent triage, provenance shape, live Hermes call, demo fallback.
All tests pass with DEMO_MODE=true and no live API credentials.
call_hermes is monkeypatched; no network calls are made.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("DEMO_MODE", "true")

from skills.guest_comms_skill import draft_guest_comms  # noqa: E402


def _ctx() -> dict:
    """Return a representative guest inquiry context dict."""
    return {
        "guest_context": "Hi, is your place available July 4th weekend? We have a dog.",
        "property_id": "clementine-001",
        "inquiry_type": "booking_inquiry",
    }


def test_demo_path_returns_required_keys() -> None:
    """Demo path (live=False) must return intent, message, upsell, reasoning_provenance."""
    result = draft_guest_comms(**_ctx())
    assert set(result.keys()) >= {"intent", "message", "upsell", "reasoning_provenance"}


def test_demo_path_provenance_shape() -> None:
    """Demo provenance must carry mode=demo, source=hermes, latency_ms, model keys."""
    result = draft_guest_comms(**_ctx())
    prov = result["reasoning_provenance"]
    assert set(prov.keys()) == {"mode", "model", "latency_ms", "source"}
    assert prov["mode"] == "demo"
    assert prov["source"] == "hermes"
    assert isinstance(prov["latency_ms"], float)
    assert isinstance(prov["model"], str) and prov["model"]


def test_demo_path_non_empty_strings() -> None:
    """Demo result fields must be non-empty strings."""
    result = draft_guest_comms(**_ctx())
    assert isinstance(result["intent"], str) and result["intent"]
    assert isinstance(result["message"], str) and result["message"]
    assert isinstance(result["upsell"], str) and result["upsell"]


def test_live_path_calls_hermes(monkeypatch) -> None:
    """live=True with a key present must call call_hermes once; provenance mode=live."""
    import skills.guest_comms_skill as m
    called = {"n": 0}

    fake_reply = json.dumps({
        "intent": "booking_inquiry",
        "message": "Yes, available! Dogs welcome.",
        "upsell": "Add a beach gear kit for $25.",
    })

    def fake_call(messages, **kwargs):
        called["n"] += 1
        return fake_reply

    monkeypatch.setattr(m, "hermes_available", lambda: True)
    monkeypatch.setattr(m, "call_hermes", fake_call)

    result = draft_guest_comms(**_ctx(), live=True)

    assert called["n"] == 1, "call_hermes must be invoked when live=True"
    assert result["reasoning_provenance"]["mode"] == "live"
    assert result["reasoning_provenance"]["source"] == "hermes"
    assert result["reasoning_provenance"]["latency_ms"] >= 0.0
    assert result["intent"] == "booking_inquiry"
    assert result["message"] == "Yes, available! Dogs welcome."
    assert result["upsell"] == "Add a beach gear kit for $25."


def test_live_path_json_parse_failure_fallback(monkeypatch) -> None:
    """Malformed Hermes JSON falls back: raw text in message, intent='general'."""
    import skills.guest_comms_skill as m

    monkeypatch.setattr(m, "hermes_available", lambda: True)
    monkeypatch.setattr(m, "call_hermes", lambda *a, **kw: "not json at all")

    result = draft_guest_comms(**_ctx(), live=True)

    assert result["intent"] == "general"
    assert "not json at all" in result["message"]
    assert result["reasoning_provenance"]["mode"] == "live"


def test_live_false_does_not_call_hermes(monkeypatch) -> None:
    """live=False must NOT call call_hermes even when a key is present."""
    import skills.guest_comms_skill as m
    called = {"n": 0}

    monkeypatch.setattr(m, "hermes_available", lambda: True)
    monkeypatch.setattr(m, "call_hermes", lambda *a, **kw: called.update({"n": 1}) or "")

    result = draft_guest_comms(**_ctx(), live=False)

    assert called["n"] == 0, "call_hermes must NOT be invoked when live=False"
    assert result["reasoning_provenance"]["mode"] == "demo"


def test_live_true_no_key_falls_back_to_demo(monkeypatch) -> None:
    """live=True with NO key must skip the call and return demo provenance."""
    import skills.guest_comms_skill as m
    called = {"n": 0}

    monkeypatch.setattr(m, "hermes_available", lambda: False)
    monkeypatch.setattr(m, "call_hermes", lambda *a, **kw: called.update({"n": 1}) or "")

    result = draft_guest_comms(**_ctx(), live=True)

    assert called["n"] == 0, "no key means no live call"
    assert result["reasoning_provenance"]["mode"] == "demo"
