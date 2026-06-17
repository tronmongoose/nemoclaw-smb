"""
vendor_analyzer.py — Rank vendor alternatives by monthly savings and build Nemotron prompts.

Exports:
    rank_alternatives(current, alternatives) -> list[dict]
    build_analysis_prompt(current, alternatives, context) -> str
"""

from __future__ import annotations


def _monthly_equivalent(vendor: dict) -> float:
    """Return pre-computed monthly_equivalent or derive from amount/frequency."""
    if "monthly_equivalent" in vendor:
        return float(vendor["monthly_equivalent"])
    freq = vendor.get("frequency", "monthly")
    amount = float(vendor.get("amount", 0))
    if freq == "annual":
        return round(amount / 12, 2)
    if freq == "quarterly":
        return round(amount / 3, 2)
    return amount


def rank_alternatives(current: dict, alternatives: list[dict]) -> list[dict]:
    """Rank alternatives by monthly savings vs current, descending.

    Each returned dict is a shallow copy of the alternative annotated with
    {monthly_savings, annual_savings, rank}. Alternatives with negative
    savings (more expensive than current) are included but ranked last.
    """
    current_mo = _monthly_equivalent(current)
    scored: list[dict] = []
    for alt in alternatives:
        alt_mo = _monthly_equivalent(alt)
        mo_savings = round(current_mo - alt_mo, 2)
        scored.append({
            **alt,
            "monthly_savings": mo_savings,
            "annual_savings": round(mo_savings * 12, 2),
        })
    scored.sort(key=lambda x: x["monthly_savings"], reverse=True)
    for i, item in enumerate(scored):
        item["rank"] = i + 1
    return scored


def build_analysis_prompt(
    current: dict,
    alternatives: list[dict],
    context: dict,
) -> str:
    """Compose a Nemotron 3 Ultra prompt for vendor-switch analysis.

    Instructs the model to use ONLY the provided data and return 'skip'
    when context is too thin to support a recommendation.
    Does NOT call any LLM. Returns the prompt string only.
    """
    #COMPLETION_DRIVE: alternatives passed here should already be ranked via rank_alternatives
    alts_lines = "\n".join(
        f"  [{a.get('rank', i+1)}] {a['vendor']} "
        f"${_monthly_equivalent(a):.2f}/mo "
        f"(saves ${a.get('monthly_savings', 0):.2f}/mo, "
        f"${a.get('annual_savings', 0):.2f}/yr)"
        for i, a in enumerate(alternatives)
    )
    ctx_lines = "\n".join(f"  {k}: {v}" for k, v in context.items())
    return (
        "You are a procurement analysis assistant. "
        "Use ONLY the structured data provided below as your source of truth. "
        "Do not draw on any prior knowledge or training data. "
        "If the context is too thin to support a recommendation, return exactly: skip\n\n"
        "## Current Vendor\n"
        f"  vendor: {current.get('vendor')}\n"
        f"  monthly_cost: ${_monthly_equivalent(current):.2f}\n\n"
        "## Ranked Alternatives\n"
        f"{alts_lines}\n\n"
        "## Additional Context\n"
        f"{ctx_lines}\n\n"
        "## Task\n"
        "1. Identify the best-value alternative and justify the switch.\n"
        "2. Note any risks or trade-offs (feature gaps, migration effort).\n"
        "3. State your confidence (high / medium / low) and why.\n"
        "Return your answer in plain text. If context is insufficient, return: skip"
    )
