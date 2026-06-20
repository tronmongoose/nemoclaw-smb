"""export.py — Serialize tenant analysis results to analysis.json for the local dashboard.

Exports: write_analysis_json

Schema written to data_root/analysis.json:
{
  "tenant": str,
  "generated_at": str (ISO, caller-supplied),
  "pnl": {
    "totals": {"income": float, "expense": float, "net": float, "margin_pct": float},
    "by_month": [{"month": str, "income": float, "expense": float, "net": float}, ...],
    "expense_by_category": [{"category": str, "amount": float}, ...],
  },
  "findings": [
    {"title": str, "category": str, "monthly_impact": float, "annual_impact": float,
     "confidence": str, "why": str},
    ...
  ],
}
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.tenancy import Tenant
    from analysis.findings import Finding

_log = logging.getLogger(__name__)


def _by_month(pnl: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive flat by_month list from pnl["monthly"] dict."""
    return [
        {
            "month": month,
            "income": data["income"],
            "expense": data["expense"],
            "net": data["net"],
        }
        for month, data in sorted(pnl.get("monthly", {}).items())
    ]


def _expense_by_category(pnl: dict[str, Any]) -> list[dict[str, Any]]:
    """Aggregate expense by_category across all months into a ranked list."""
    cat_totals: dict[str, float] = {}
    for data in pnl.get("monthly", {}).values():
        for cat, amt in data.get("by_category", {}).items():
            cat_totals[cat] = round(cat_totals.get(cat, 0.0) + amt, 2)
    return sorted(
        [{"category": cat, "amount": amt} for cat, amt in cat_totals.items()],
        key=lambda x: -x["amount"],
    )


def _margin_pct(totals: dict[str, Any]) -> float:
    """Return net/income*100; guards divide-by-zero."""
    income = totals.get("income", 0.0)
    net = totals.get("net", 0.0)
    if income == 0.0:
        return 0.0
    return round(net / income * 100, 2)


def write_analysis_json(
    tenant: "Tenant",
    pnl: dict[str, Any],
    findings: list["Finding"],
    generated_at: str,
) -> str:
    """Write analysis.json to tenant.data_root and return the path.

    #COMPLETION_DRIVE: caller supplies generated_at as an ISO string;
    this function never calls datetime.now to keep the function pure/testable.
    """
    totals = pnl.get("totals", {})
    payload: dict[str, Any] = {
        "tenant": tenant.slug,
        "generated_at": generated_at,
        "pnl": {
            "totals": {
                "income": totals.get("income", 0.0),
                "expense": totals.get("expense", 0.0),
                "net": totals.get("net", 0.0),
                "margin_pct": _margin_pct(totals),
            },
            "by_month": _by_month(pnl),
            "expense_by_category": _expense_by_category(pnl),
        },
        "findings": [
            {
                "title": f.title,
                "category": f.category,
                "monthly_impact": f.monthly_impact,
                "annual_impact": f.annual_impact,
                "confidence": f.confidence,
                "why": f.why,
            }
            for f in findings
        ],
    }

    out_path = Path(tenant.data_root) / "analysis.json"
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _log.info("export: wrote %s", out_path)
    except OSError as exc:
        _log.warning("export: could not write analysis.json: %s", exc)

    return str(out_path)
