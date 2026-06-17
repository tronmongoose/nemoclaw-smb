"""
vendor_analyze_skill.py — Rank vendor alternatives and invoke Nemotron procurement analysis.

This is the Nemotron-backed heavy skill: rank_alternatives provides the savings math,
analyze_vendors calls NIM for procurement reasoning (mock offline).

Exports: skill (registered on import)
"""

from __future__ import annotations

from agent.reasoning import analyze_vendors
from procurement.vendor_analyzer import rank_alternatives

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "current": {
            "type": "object",
            "description": "Current vendor dict with keys: vendor, amount, frequency.",
        },
        "alternatives": {
            "type": "array",
            "description": "List of alternative vendor dicts (vendor, amount, frequency).",
        },
        "context": {
            "type": "object",
            "description": "Additional context passed to Nemotron for reasoning.",
            "default": {},
        },
    },
    "required": ["current", "alternatives"],
}


def _run(args: dict) -> dict:
    """Rank alternatives by savings and return Nemotron procurement analysis."""
    current: dict = args["current"]
    alternatives: list[dict] = args["alternatives"]
    context: dict = args.get("context") or {}

    ranked = rank_alternatives(current, alternatives)
    reasoning = analyze_vendors(current, alternatives, context)

    return {
        "ranked_alternatives": ranked,
        "reasoning": reasoning,
    }


skill = register(Skill(
    name="vendor_analyze_skill",
    description="Rank vendor alternatives by monthly savings and analyze with Nemotron 3 Ultra.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
