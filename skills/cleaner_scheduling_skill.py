"""skills/cleaner_scheduling_skill.py: Cleaner reassign + schedule skill.

When a clean stage stalls, Nous Hermes drafts the reassignment: which free
cleaner to move it to, a near-term slot, and the card pre-authorization. The
suggested cleaner comes from the data (so the card is issued to the right crew
id); only the reasoning prose is Hermes. Mirrors coordination_skill. Never raises.

Public API:
    draft_cleaner_schedule(clean_stall, live=False) -> dict
        Returns {"suggested_cleaner", "scheduled_start", "reason",
                 "card_action", "reasoning_provenance"}
"""
from __future__ import annotations

import json
import os
import time

from agent.hermes_client import call_hermes, hermes_available
from config.model_routing import route_for

_SYSTEM_PROMPT: str = (
    "You are a short-term-rental operations scheduler. A cleaning is stalled. "
    "In one or two sentences, tell the manager who to reassign it to and why, "
    "and that a single-use card will be pre-authorized. Always reply as compact JSON."
)

_SCHEDULED_START: str = "today, 2:30pm (next free 90-min window)"
_CARD_ACTION: str = "pre-authorize $75 single-use card (MCC cleaning, end-of-day expiry)"


def _hermes_model() -> str:
    """Return the Hermes model identifier from the environment or routing table."""
    return os.environ.get("HERMES_MODEL", route_for("cleaner_scheduling"))


def _suggested_name(clean_stall: dict) -> str:
    """Return the suggested free cleaner's name, or a neutral placeholder."""
    sug = clean_stall.get("suggested_cleaner") or {}
    return sug.get("name", "an available cleaner")


def _demo_reason(clean_stall: dict) -> str:
    """Compose a deterministic reassignment reason from the stall data."""
    name = clean_stall.get("property_name", "this property")
    assigned = clean_stall.get("assigned_to", "the assigned cleaner")
    suggested = _suggested_name(clean_stall)
    hours = clean_stall.get("hours_stalled", 0)
    return (
        f"{name} cleaning has sat {hours}h with {assigned}, who is booked. "
        f"{suggested} is free now. Reassign to {suggested} for a {_SCHEDULED_START} start "
        "and pre-authorize a single-use card so the turnover stays on track."
    )


def _parse_hermes_json(raw: str, fallback_reason: str) -> str:
    """Parse Hermes JSON {reason}; fall back to raw text on failure."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            return str(parsed.get("reason", raw))
    except (json.JSONDecodeError, ValueError):
        pass
    return raw or fallback_reason


def draft_cleaner_schedule(clean_stall: dict, *, live: bool = False) -> dict:
    """Draft the reassignment + schedule for a stalled clean stage.

    When live is True and a Nous key is present, makes one call_hermes call for
    the reasoning prose. The suggested cleaner and slot are deterministic so the
    downstream card issuance targets the right crew id. Never raises.
    """
    model = _hermes_model()
    suggested_name = _suggested_name(clean_stall)
    demo_reason = _demo_reason(clean_stall)

    if live and hermes_available():
        user_content = (
            f"Stalled cleaning JSON: {json.dumps(clean_stall)}. "
            f"Reassign to {suggested_name}, start {_SCHEDULED_START}. "
            "Respond with JSON: {\"reason\": \"...\"}."
        )
        messages = [{"role": "user", "content": user_content}]
        start = time.perf_counter()
        raw = call_hermes(messages, max_tokens=300, temperature=0.3, system=_SYSTEM_PROMPT)
        latency_ms = (time.perf_counter() - start) * 1000.0
        reason = _parse_hermes_json(raw, demo_reason)
        provenance = {
            "mode": "live",
            "model": model,
            "latency_ms": latency_ms,
            "source": "hermes",
        }
        return {
            "suggested_cleaner": suggested_name,
            "scheduled_start": _SCHEDULED_START,
            "reason": reason,
            "card_action": _CARD_ACTION,
            "reasoning_provenance": provenance,
        }

    provenance = {
        "mode": "demo",
        "model": f"{model}[demo-cached]",
        "latency_ms": 0.0,
        "source": "hermes",
    }
    return {
        "suggested_cleaner": suggested_name,
        "scheduled_start": _SCHEDULED_START,
        "reason": demo_reason,
        "card_action": _CARD_ACTION,
        "reasoning_provenance": provenance,
    }
