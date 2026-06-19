"""pnl.py — Monthly P&L computation from normalized transaction list.

Pure arithmetic; no LLM.

Exports: compute_pnl

compute_pnl returns:
{
    "monthly": {
        "YYYY-MM": {
            "income": float,
            "expense": float,
            "net": float,
            "by_category": {"category": total, ...}
        },
        ...
    },
    "totals": {"income": float, "expense": float, "net": float},
    "margin_trend": [{"month": str, "net": float}, ...],  # sorted ascending
}
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _month_key(iso_date: str) -> str:
    """Extract YYYY-MM from an ISO date string."""
    return iso_date[:7] if len(iso_date) >= 7 else iso_date


def compute_pnl(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate transactions into monthly P&L buckets.

    Each transaction must have: date (ISO), amount (float >= 0),
    direction ("expense"|"income"), category (str|None).
    """
    monthly: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"income": 0.0, "expense": 0.0, "net": 0.0, "by_category": defaultdict(float)}
    )

    for tx in transactions:
        month = _month_key(tx.get("date", ""))
        if not month:
            continue
        amount = float(tx.get("amount", 0.0))
        direction = tx.get("direction", "expense")
        category = tx.get("category") or "Other"

        bucket = monthly[month]
        if direction == "income":
            bucket["income"] += amount
        else:
            bucket["expense"] += amount
        bucket["net"] = bucket["income"] - bucket["expense"]
        bucket["by_category"][category] += amount if direction == "expense" else -amount

    # Convert defaultdicts to plain dicts for serialisation
    result_monthly: dict[str, dict[str, Any]] = {}
    for month in sorted(monthly.keys()):
        b = monthly[month]
        result_monthly[month] = {
            "income": round(b["income"], 2),
            "expense": round(b["expense"], 2),
            "net": round(b["net"], 2),
            "by_category": {k: round(v, 2) for k, v in b["by_category"].items()},
        }

    total_income = sum(m["income"] for m in result_monthly.values())
    total_expense = sum(m["expense"] for m in result_monthly.values())

    return {
        "monthly": result_monthly,
        "totals": {
            "income": round(total_income, 2),
            "expense": round(total_expense, 2),
            "net": round(total_income - total_expense, 2),
        },
        "margin_trend": [
            {"month": m, "net": result_monthly[m]["net"]}
            for m in sorted(result_monthly.keys())
        ],
    }
