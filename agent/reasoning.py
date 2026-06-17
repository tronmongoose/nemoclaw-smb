"""
reasoning.py — Thin wrappers that build prompts and call Nemotron 3 Ultra.

Exports: reason_about_anomaly, analyze_vendors, draft_negotiation.
"""

from __future__ import annotations

from gbrain.anomaly_detector import Anomaly, build_nemotron_prompt
from procurement.negotiation_drafter import draft_outreach_prompt
from procurement.vendor_analyzer import build_analysis_prompt, rank_alternatives

from agent.nvidia_client import call_nemotron


def reason_about_anomaly(anomaly: Anomaly, context: dict) -> str:
    """Build an anomaly reasoning prompt and invoke Nemotron 3 Ultra.

    Returns Nemotron's final-answer text, or the mock prefix string offline.
    """
    prompt = build_nemotron_prompt(anomaly, context)
    return call_nemotron(prompt)


def analyze_vendors(
    current: dict,
    alternatives: list[dict],
    context: dict,
) -> str:
    """Rank alternatives, build analysis prompt, and invoke Nemotron 3 Ultra.

    Returns Nemotron's procurement analysis text, or the mock prefix offline.
    """
    ranked = rank_alternatives(current, alternatives)
    prompt = build_analysis_prompt(current, ranked, context)
    return call_nemotron(prompt)


def draft_negotiation(vendor: str, anomaly: dict, context: dict) -> str:
    """Build a negotiation outreach prompt and invoke Nemotron 3 Ultra.

    Returns Nemotron's drafted email text, or the mock prefix offline.
    """
    prompt = draft_outreach_prompt(vendor, anomaly, context)
    return call_nemotron(prompt)
