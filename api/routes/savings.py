"""Savings and vendor-alternative routes for nemoclaw-smb dashboard.

Exports (via router):
    GET /savings/alternatives  — ranked alternatives for a given current vendor
    GET /savings/summary       — total spend, projected savings, nemoclaw fee
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from fixtures.seed_data import seed_alternatives, seed_invoices
from procurement.vendor_analyzer import rank_alternatives

router = APIRouter(prefix="/savings", tags=["savings"])

_NEMOCLAW_FEE_RATE: float = 0.005

# Precompute totals once at module load (seed data is deterministic).
#GLOBAL-STATE: precomputed from seed_invoices; recalculated only if savings router is reloaded
_TOTAL_SPEND: float = sum(inv["amount"] for inv in seed_invoices())

_ADOBE_CURRENT = {
    "vendor": "Adobe Creative Cloud",
    "amount": 340.0,       # June anomaly amount — the current spike being evaluated
    "frequency": "monthly",
    "monthly_equivalent": 340.0,
}


def _ranked_alternatives(current_vendor: str) -> list[dict]:
    """Return ranked alternatives for the given current vendor.

    Only Adobe Creative Cloud is seeded. Other vendors return an empty list.
    #COMPLETION_DRIVE: only Adobe alternatives are seeded; extend seed_alternatives() to add more
    """
    if current_vendor.lower() == "adobe creative cloud":
        current = _ADOBE_CURRENT
        alts = seed_alternatives()
        return rank_alternatives(current, alts)
    return []


@router.get("/alternatives")
def get_alternatives(
    current_vendor: str = Query(default="Adobe Creative Cloud"),
) -> dict:
    """Return current vendor info and ranked cheaper alternatives.

    Response shape:
        {
          current:  {vendor, amount},
          ranked:   [{vendor, amount, monthly_savings, annual_savings, rank}, ...]
        }
    """
    if current_vendor.lower() == "adobe creative cloud":
        current_info = {"vendor": _ADOBE_CURRENT["vendor"], "amount": _ADOBE_CURRENT["amount"]}
    else:
        current_info = {"vendor": current_vendor, "amount": 0.0}

    ranked = _ranked_alternatives(current_vendor)
    ranked_out = [
        {
            "vendor": r["vendor"],
            "amount": r.get("monthly_equivalent", r.get("amount", 0.0)),
            "monthly_savings": r["monthly_savings"],
            "annual_savings": r["annual_savings"],
            "rank": r["rank"],
        }
        for r in ranked
    ]
    return {"current": current_info, "ranked": ranked_out}


@router.get("/summary")
def get_summary() -> dict:
    """Return total spend, projected monthly/annual savings, and NemoClaw fee.

    fee_rate is fixed at 0.005 (50 bps).
    monthly_savings and annual_savings are derived from the top-ranked Adobe alternative.
    """
    ranked = _ranked_alternatives("Adobe Creative Cloud")
    top = ranked[0] if ranked else {}
    monthly_savings = top.get("monthly_savings", 0.0)
    annual_savings = top.get("annual_savings", 0.0)
    fee = round(_TOTAL_SPEND * _NEMOCLAW_FEE_RATE, 2)
    return {
        "total_spend": _TOTAL_SPEND,
        "monthly_savings": monthly_savings,
        "annual_savings": annual_savings,
        "nemoclaw_fee": fee,
        "fee_rate": _NEMOCLAW_FEE_RATE,
        "currency": "USD",
    }
