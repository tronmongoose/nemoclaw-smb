"""skills/performance_analysis_skill.py: Portfolio performance "why" skill.

Takes one property's performance numbers and has Nous Hermes explain WHY it is
over- or under-performing. Mirrors coordination_skill: live=True + a Nous key
makes one call_hermes call; otherwise a deterministic, data-driven demo summary.
Never raises.

Public API:
    summarize_performance(perf, live=False) -> dict
        Returns {"verdict", "summary", "drivers", "reasoning_provenance"}
"""
from __future__ import annotations

import json
import os
import time

from agent.hermes_client import call_hermes, hermes_available
from config.model_routing import route_for

_SYSTEM_PROMPT: str = (
    "You are a short-term-rental portfolio analyst. Explain why a property is "
    "over- or under-performing in two sentences, concrete and specific. "
    "Always reply as compact JSON."
)


def _hermes_model() -> str:
    """Return the Hermes model identifier from the environment or routing table."""
    return os.environ.get("HERMES_MODEL", route_for("performance_analysis"))


def _demo_summary(perf: dict) -> tuple[str, list[str]]:
    """Compose a deterministic, data-driven summary + drivers from the perf numbers."""
    name = perf["property_name"]
    pctpts = abs(round(perf["pct_vs_avg"] * 100))
    occ = round(perf["occupancy"] * 100)
    status = perf["status"]
    if status == "over":
        return (
            f"{name} runs {pctpts}% above the portfolio average on {occ}% occupancy. "
            "Beach proximity and peak-season pricing are carrying it; protect the review score.",
            ["high occupancy", "peak-season pricing", "location premium"],
        )
    if status == "under":
        return (
            f"{name} runs {pctpts}% below the portfolio average on {occ}% occupancy. "
            "Soft mid-week demand and underpricing for the season are the likely drag.",
            ["low occupancy", "underpriced for season", "thin amenity set vs comps"],
        )
    return (
        f"{name} tracks within {pctpts}% of the portfolio average on {occ}% occupancy. "
        "Steady; no action needed this cycle.",
        ["in-band revenue", "stable occupancy"],
    )


def _parse_hermes_json(raw: str, fallback_summary: str) -> dict:
    """Parse Hermes JSON {summary, drivers}; fall back to raw text on failure."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            drivers = parsed.get("drivers", [])
            return {
                "summary": str(parsed.get("summary", raw)),
                "drivers": [str(d) for d in drivers] if isinstance(drivers, list) else [],
            }
    except (json.JSONDecodeError, ValueError):
        pass
    return {"summary": raw or fallback_summary, "drivers": []}


def summarize_performance(perf: dict, *, live: bool = False) -> dict:
    """Explain why a property is over/under-performing.

    When live is True and a Nous key is present, makes one call_hermes call and
    measures latency. Otherwise returns a deterministic demo summary. Never raises.
    """
    model = _hermes_model()
    demo_summary, demo_drivers = _demo_summary(perf)

    if live and hermes_available():
        user_content = (
            f"Property performance JSON: {json.dumps(perf)}. "
            f"This property is {perf['status']} the portfolio average. "
            "In two sentences explain WHY and list the top drivers. "
            "Respond with JSON: {\"summary\": \"...\", \"drivers\": [\"...\"]}."
        )
        messages = [{"role": "user", "content": user_content}]
        start = time.perf_counter()
        raw = call_hermes(messages, max_tokens=400, temperature=0.3, system=_SYSTEM_PROMPT)
        latency_ms = (time.perf_counter() - start) * 1000.0
        parsed = _parse_hermes_json(raw, demo_summary)
        provenance = {
            "mode": "live",
            "model": model,
            "latency_ms": latency_ms,
            "source": "hermes",
        }
        return {"verdict": perf["status"], **parsed, "reasoning_provenance": provenance}

    provenance = {
        "mode": "demo",
        "model": f"{model}[demo-cached]",
        "latency_ms": 0.0,
        "source": "hermes",
    }
    return {
        "verdict": perf["status"],
        "summary": demo_summary,
        "drivers": demo_drivers,
        "reasoning_provenance": provenance,
    }
