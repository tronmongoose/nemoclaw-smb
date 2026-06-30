"""skills/coordination_skill.py: Turnover coordination skill.

Reasons over a stalled turnover handoff via Nous Hermes and drafts the nudge
that unsticks it (who is blocking, what to say, what to do next). Mirrors
guest_comms_skill: live=True + a Nous key makes one call_hermes call; otherwise
a deterministic demo result. Never raises.

Public API:
    draft_coordination_nudge(handoff, live=False) -> dict
        Returns {"stalled_actor", "nudge_message", "next_action", "reasoning_provenance"}
        reasoning_provenance: {mode, model, latency_ms, source}
"""
from __future__ import annotations

import json
import os
import time

from agent.hermes_client import call_hermes, hermes_available
from config.model_routing import route_for

_SYSTEM_PROMPT: str = (
    "You are a short-term-rental operations coordinator. You keep the turnover "
    "loop (checkout -> clean -> inspect -> ready-to-book) moving by nudging the "
    "party that is blocking the next handoff. Always reply as compact JSON."
)

_DEMO_RESULT: dict = {
    "stalled_actor": "inspector",
    "nudge_message": (
        "Hi Maria, Sweet Clementine finished cleaning at 2:31pm but the inspection "
        "hasn't started, so we can't reopen the listing. Can you confirm an inspector "
        "for the next hour, or should I reassign? Reply here and I'll update the board."
    ),
    "next_action": "assign_inspector_then_reopen_listing",
}


def _hermes_model() -> str:
    """Return the Hermes model identifier from the environment or routing table."""
    return os.environ.get("HERMES_MODEL", route_for("turnover_coordination"))


def _parse_hermes_json(raw: str) -> dict:
    """Parse Hermes JSON response; fall back to raw text in 'nudge_message' on failure."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            return {
                "stalled_actor": str(parsed.get("stalled_actor", "none")),
                "nudge_message": str(parsed.get("nudge_message", raw)),
                "next_action": str(parsed.get("next_action", "escalate")),
            }
    except (json.JSONDecodeError, ValueError):
        pass
    return {"stalled_actor": "none", "nudge_message": raw, "next_action": "escalate"}


def draft_coordination_nudge(
    handoff: dict,
    *,
    live: bool = False,
) -> dict:
    """Analyze a stalled handoff and draft a nudge for the blocking party.

    When live is True and a Nous key is present, makes one call_hermes call and
    measures latency. Otherwise returns a deterministic demo result. Never raises;
    JSON parse failures fall back safely. live defaults False.
    """
    model = _hermes_model()

    if live and hermes_available():
        user_content = (
            f"Property: {handoff.get('property_name')}. "
            f"Stalled stage: {handoff.get('stage')}. "
            f"Handoff: {handoff.get('from_actor')} -> {handoff.get('to_actor')}. "
            f"Assigned to: {handoff.get('assigned_to')}. "
            f"Stalled {handoff.get('hours_stalled')}h. Reason: {handoff.get('reason')}. "
            "Respond with JSON: {\"stalled_actor\": \"...\", \"nudge_message\": \"...\", "
            "\"next_action\": \"...\"}."
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
