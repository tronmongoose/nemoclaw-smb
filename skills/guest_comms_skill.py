"""skills/guest_comms_skill.py: Guest communications (Sales) skill.

Triages a guest inquiry's intent via Nous Hermes, then drafts an on-brand
host reply plus one upsell. First live use of call_hermes in this codebase.

Public API:
    draft_guest_comms(guest_context, property_id, inquiry_type, live=False) -> dict
        Returns {"intent", "message", "upsell", "reasoning_provenance"}
        reasoning_provenance: {mode, model, latency_ms, source}
"""
from __future__ import annotations

import json
import os
import time

from agent.hermes_client import call_hermes, hermes_available
from config.model_routing import route_for

_SYSTEM_PROMPT: str = (
    "You are a short-term-rental host's sales agent. Always reply as compact JSON."
)

_DEMO_RESULT: dict = {
    "intent": "booking_inquiry",
    "message": (
        "Hi! Thanks for reaching out about Sweet Clementine. "
        "We are available for your dates. Check-in is 4pm, checkout 11am. "
        "The property sleeps 6, is dog-friendly (max 2 dogs, $30/night/pet), "
        "and is a 10-minute walk to Strand Beach. Happy to answer any questions!"
    ),
    "upsell": (
        "Extend your stay by one night and get the fire-pit backyard for a full "
        "weekend sunset session. Weekend pricing is very competitive right now."
    ),
}


def _hermes_model() -> str:
    """Return the Hermes model identifier from the environment or routing table."""
    return os.environ.get("HERMES_MODEL", route_for("guest_comms"))


def _parse_hermes_json(raw: str) -> dict:
    """Parse Hermes JSON response; fall back to raw text in 'message' on failure."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            return {
                "intent": str(parsed.get("intent", "general")),
                "message": str(parsed.get("message", raw)),
                "upsell": str(parsed.get("upsell", "")),
            }
    except (json.JSONDecodeError, ValueError):
        pass
    return {"intent": "general", "message": raw, "upsell": ""}


def draft_guest_comms(
    guest_context: str,
    property_id: str,
    inquiry_type: str,
    *,
    live: bool = False,
) -> dict:
    """Triage a guest inquiry and draft a reply with one upsell.

    When live is True and a Nous key is present, makes one call_hermes call
    and measures latency. Otherwise returns a deterministic demo result.
    Never raises; JSON parse failures fall back safely. live defaults False.
    """
    model = _hermes_model()

    if live and hermes_available():
        user_content = (
            f"Property: {property_id}. Inquiry type: {inquiry_type}. "
            f"Guest message: {guest_context}. "
            "Respond with JSON: {\"intent\": \"...\", \"message\": \"...\", \"upsell\": \"...\"}."
        )
        messages = [{"role": "user", "content": user_content}]
        start = time.perf_counter()
        raw = call_hermes(messages, max_tokens=512, temperature=0.3, system=_SYSTEM_PROMPT)
        latency_ms = (time.perf_counter() - start) * 1000.0
        parsed = _parse_hermes_json(raw)
        provenance = {
            "mode": "live",
            "model": model,
            "latency_ms": latency_ms,
            "source": "hermes",
        }
        return {**parsed, "reasoning_provenance": provenance}

    provenance = {
        "mode": "demo",
        "model": f"{model}[demo-cached]",
        "latency_ms": 0.0,
        "source": "hermes",
    }
    return {**_DEMO_RESULT, "reasoning_provenance": provenance}
