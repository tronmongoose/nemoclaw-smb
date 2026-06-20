"""export.py — Serialize tenant analysis results to analysis.json for the local dashboard.

Exports: write_analysis_json

Schema written to data_root/analysis.json (v2 — superset of v1; all v1 keys preserved):
{
  "tenant": str,
  "generated_at": str (ISO, caller-supplied),
  "pnl": {
    "totals": {"income": float, "expense": float, "net": float, "margin_pct": float},
    "by_month": [{"month": str, "income": float, "expense": float, "net": float}, ...],
    "expense_by_category": [{"category": str, "amount": float}, ...],
  },
  "headlines": [                    // top 3 findings by annual_impact; each has a series
    {
      "title": str,
      "action": str,
      "annual_impact": float,
      "monthly_impact": float,
      "severity": str,              // alias for confidence
      "category": str,
      "series": [{"month": str, "value": float}, ...]  // per-category monthly expense
    }, ...
  ],
  "findings": [                     // full ranked list; includes action field
    {"title": str, "category": str, "action": str,
     "annual_impact": float, "monthly_impact": float, "confidence": str, "why": str},
    ...
  ],
  "longitudinal": {
    "net_by_month": [{"month": str, "net": float}, ...],
    "by_category_monthly": [{"category": str, "series": [{"month": str, "value": float}]}, ...]
  }
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
    """Derive flat by_month list from pnl['monthly'] dict."""
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


def _net_by_month(pnl: dict[str, Any]) -> list[dict[str, Any]]:
    """Return net for each month across all loaded months, sorted ascending."""
    return [
        {"month": month, "net": data["net"]}
        for month, data in sorted(pnl.get("monthly", {}).items())
    ]


def _category_monthly_series(
    pnl: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return per-expense-category monthly series spanning all loaded months.

    Only expense-positive categories are included (income offsets are excluded).
    Series is sorted ascending by month.

    #COMPLETION_DRIVE: pnl['monthly'][m]['by_category'] holds net expense per category
    (positive = net expense, negative = net income for that category). We include
    categories with at least one positive month to avoid income categories.
    """
    all_months = sorted(pnl.get("monthly", {}).keys())
    cat_months: dict[str, dict[str, float]] = {}

    for month, data in pnl.get("monthly", {}).items():
        for cat, amt in data.get("by_category", {}).items():
            if cat not in cat_months:
                cat_months[cat] = {}
            cat_months[cat][month] = amt

    result = []
    for cat, month_map in cat_months.items():
        # Skip income-only categories (all values <= 0)
        if all(v <= 0 for v in month_map.values()):
            continue
        series = [
            {"month": m, "value": round(month_map.get(m, 0.0), 2)}
            for m in all_months
        ]
        result.append({"category": cat, "series": series})

    result.sort(key=lambda x: x["category"])
    return result


def _category_series_map(
    pnl: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Return {category: series} for quick lookup when building headlines."""
    return {item["category"]: item["series"] for item in _category_monthly_series(pnl)}


def _build_headlines(
    findings: list["Finding"],
    cat_series: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return up to 3 headline objects from top findings by annual_impact.

    Each headline includes a per-category monthly expense series for trend display.
    """
    headlines = []
    for f in findings[:3]:
        series = cat_series.get(f.category, [])
        headlines.append({
            "title": f.title,
            "action": f.action,
            "annual_impact": f.annual_impact,
            "monthly_impact": f.monthly_impact,
            "severity": f.confidence,
            "category": f.category,
            "series": series,
        })
    return headlines


def write_analysis_json(
    tenant: "Tenant",
    pnl: dict[str, Any],
    findings: list["Finding"],
    generated_at: str,
) -> str:
    """Write analysis.json (v2) to tenant.data_root and return the path.

    #COMPLETION_DRIVE: caller supplies generated_at as an ISO string;
    this function never calls datetime.now to keep the function pure/testable.
    Findings must be pre-sorted by annual_impact desc (find() guarantees this).
    """
    totals = pnl.get("totals", {})
    cat_series = _category_series_map(pnl)

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
        "headlines": _build_headlines(findings, cat_series),
        "findings": [
            {
                "title": f.title,
                "category": f.category,
                "action": f.action,
                "annual_impact": f.annual_impact,
                "monthly_impact": f.monthly_impact,
                "confidence": f.confidence,
                "why": f.why,
            }
            for f in findings
        ],
        "longitudinal": {
            "net_by_month": _net_by_month(pnl),
            "by_category_monthly": _category_monthly_series(pnl),
        },
    }

    out_path = Path(tenant.data_root) / "analysis.json"
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _log.info("export: wrote %s", out_path)
    except OSError as exc:
        _log.warning("export: could not write analysis.json: %s", exc)

    return str(out_path)
