"""
negotiation_drafter.py — Build Nemotron prompts for vendor negotiation outreach.

Exports:
    draft_outreach_prompt(vendor, anomaly, context) -> str
"""

from __future__ import annotations


def draft_outreach_prompt(vendor: str, anomaly: dict, context: dict) -> str:
    """Compose a Nemotron 3 Ultra prompt to draft a vendor negotiation email.

    anomaly is an Anomaly dataclass or equivalent dict with keys:
        current_amount, baseline_mean, pct_change, reason.
    context carries SMB metadata (studio name, headcount, contact, etc.).

    Instructs the model to use ONLY the provided data and return 'skip'
    when context is too thin. Does NOT call any LLM; returns the prompt only.
    """
    #COMPLETION_DRIVE: anomaly may be an Anomaly dataclass or a plain dict
    def _get(obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    current_amount = _get(anomaly, "current_amount")
    baseline_mean = _get(anomaly, "baseline_mean")
    pct_change = _get(anomaly, "pct_change")
    reason = _get(anomaly, "reason")

    ctx_lines = "\n".join(f"  {k}: {v}" for k, v in context.items())

    return (
        "You are a vendor negotiation email drafting assistant. "
        "Use ONLY the structured data provided below as your source of truth. "
        "Do not draw on any prior knowledge or training data. "
        "If the context is too thin to draft a coherent email, return exactly: skip\n\n"
        "## Flagged Overcharge\n"
        f"  vendor: {vendor}\n"
        f"  billed_amount: ${float(current_amount):.2f}\n"
        f"  expected_baseline: ${float(baseline_mean):.2f}\n"
        f"  pct_change: {float(pct_change):+.1f}%\n"
        f"  reason: {reason}\n\n"
        "## Client Context\n"
        f"{ctx_lines}\n\n"
        "## Task\n"
        "Draft a concise, professional outreach email from the SMB client to the vendor. "
        "The email should:\n"
        "  1. Reference the specific charge discrepancy using the figures above.\n"
        "  2. Request a written explanation or corrected invoice.\n"
        "  3. Propose a credit or rate-lock if appropriate.\n"
        "  4. Maintain a collaborative (not adversarial) tone.\n"
        "Return only the email body (Subject line first, then body). "
        "If context is insufficient, return: skip"
    )
