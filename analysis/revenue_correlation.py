"""revenue_correlation.py — Helpers for identifying and scoring revenue-correlated costs.

Exports:
    DEFAULT_CORRELATED_SUBSTRINGS  — default case-insensitive substring list
    DEFAULT_CORR_THRESHOLD         — Pearson r floor for auto-detection
    DEFAULT_RATIO_Z_THRESHOLD      — z-score threshold for ratio anomaly
    DEFAULT_RATIO_JUMP_THRESHOLD   — relative ratio jump threshold
    pearson_r                      — Pearson correlation coefficient
    is_config_correlated           — substring match against config list
    revenue_by_month               — income totals per YYYY-MM
    category_monthly_costs         — expense totals per YYYY-MM for one category
    build_correlated_categories    — full set of revenue-correlated categories
    ratio_findings_for_category    — Finding list from ratio-based anomaly detection
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from analysis.findings import Finding

# Substrings (case-insensitive) that identify revenue-correlated cost categories
# by default. Overridable via thresholds['revenue_correlated'] list.
#
# #COMPLETION_DRIVE: covers the dominant STR cost structure; tenant-specific names
# (e.g. "owner distribution") must be added via config.
DEFAULT_CORRELATED_SUBSTRINGS: tuple[str, ...] = (
    "mgmt",
    "management",
    "platform",
    "booking",
    "host fee",
    "commission",
    "cleaning",
)

# #COMPLETION_DRIVE: 0.7 is the standard "strong positive correlation" threshold.
# Lower (0.6) catches noisier structures; higher (0.8) is more conservative.
# Tune via thresholds['corr_threshold'].
DEFAULT_CORR_THRESHOLD: float = 0.7

_MIN_MONTHS_FOR_CORR: int = 4  # minimum shared months for meaningful Pearson r

# #COMPLETION_DRIVE: ratio z-threshold matches the absolute detector default (2.0)
# for consistent sensitivity; adjustable via thresholds['ratio_z_threshold'].
DEFAULT_RATIO_Z_THRESHOLD: float = 2.0

# #COMPLETION_DRIVE: 0.30 catches a manager raising cut from 15% to 20% (+33% ratio).
# Adjustable via thresholds['ratio_jump_threshold'].
DEFAULT_RATIO_JUMP_THRESHOLD: float = 0.30


def pearson_r(xs: list[float], ys: list[float]) -> float:
    """Return Pearson r for two equal-length sequences; 0.0 on degenerate input."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sdx = statistics.pstdev(xs)
    sdy = statistics.pstdev(ys)
    if sdx == 0 or sdy == 0:
        return 0.0
    return cov / (n * sdx * sdy)


def is_config_correlated(category: str, substrings: tuple[str, ...]) -> bool:
    """True if category name contains any substring (case-insensitive)."""
    cat_lower = category.lower()
    return any(s in cat_lower for s in substrings)


def revenue_by_month(transactions: list[dict[str, Any]]) -> dict[str, float]:
    """Return total income per YYYY-MM from income-direction records."""
    monthly: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.get("direction") == "income":
            month = t.get("date", "")[:7]
            if month:
                monthly[month] += float(t.get("amount", 0.0))
    return dict(monthly)


def category_monthly_costs(
    expenses: list[dict[str, Any]],
    category: str,
) -> dict[str, float]:
    """Return total expense amount per YYYY-MM for a given category."""
    monthly: dict[str, float] = defaultdict(float)
    for t in expenses:
        if t.get("category") == category:
            month = t.get("date", "")[:7]
            if month:
                monthly[month] += float(t.get("amount", 0.0))
    return dict(monthly)


def _is_auto_correlated(
    category: str,
    expenses: list[dict[str, Any]],
    rev_by_month: dict[str, float],
    corr_threshold: float,
) -> bool:
    """True if category's monthly costs correlate >= corr_threshold with revenue."""
    cost_by_month = category_monthly_costs(expenses, category)
    shared = sorted(set(cost_by_month) & set(rev_by_month))
    if len(shared) < _MIN_MONTHS_FOR_CORR:
        return False
    costs = [cost_by_month[m] for m in shared]
    revs = [rev_by_month[m] for m in shared]
    return pearson_r(costs, revs) >= corr_threshold


def build_correlated_categories(
    expenses: list[dict[str, Any]],
    rev_by_month: dict[str, float],
    config_substrings: tuple[str, ...],
    corr_threshold: float,
) -> frozenset[str]:
    """Return all expense categories that are revenue-correlated (config OR auto-detect)."""
    all_cats = {t.get("category", "") for t in expenses if t.get("category")}
    correlated: set[str] = set()
    for cat in all_cats:
        if is_config_correlated(cat, config_substrings):
            correlated.add(cat)
        elif _is_auto_correlated(cat, expenses, rev_by_month, corr_threshold):
            correlated.add(cat)
    return frozenset(correlated)


def ratio_findings_for_category(
    category: str,
    expenses: list[dict[str, Any]],
    rev_by_month: dict[str, float],
    ratio_z_threshold: float,
    ratio_jump_threshold: float,
) -> list[Any]:  # returns list[Finding]; typed as Any to avoid circular import
    """Flag months where cost/revenue ratio is anomalous for one category.

    Suppresses months where the ratio is stable (normal seasonal pattern).
    Fires only when the ratio itself deviates — i.e. the manager raised their cut.
    The 'why' cites the percentage/ratio change, not the raw dollar delta.
    """
    from analysis.findings import Finding  # local import avoids circular reference

    cost_by_month = category_monthly_costs(expenses, category)
    # Filter zero-revenue months before any ratio computation to guarantee
    # the minimum-months guard counts only months where division is valid.
    shared = sorted(
        m for m in set(cost_by_month) & set(rev_by_month)
        if rev_by_month[m] > 0
    )
    if len(shared) < 2:
        return []

    ratios: list[tuple[str, float]] = [
        (m, cost_by_month[m] / rev_by_month[m])
        for m in shared
    ]
    if len(ratios) < 2:
        return []

    findings: list[Finding] = []
    for i, (month, ratio) in enumerate(ratios):
        history = [r for _, r in ratios[:i]]
        if len(history) < 2:
            continue
        hist_mean = statistics.mean(history)
        hist_std = statistics.pstdev(history)

        z = (ratio - hist_mean) / hist_std if hist_std > 0 else 0.0
        rel_jump = (ratio - hist_mean) / hist_mean if hist_mean > 0 else 0.0

        if z >= ratio_z_threshold or rel_jump >= ratio_jump_threshold:
            rev = rev_by_month[month]
            cost = cost_by_month[month]
            delta_cost = cost - hist_mean * rev
            prior_pct = round(hist_mean * 100, 1)
            curr_pct = round(ratio * 100, 1)
            findings.append(Finding(
                title=f"Expense spike: {category}",
                category=category,
                monthly_impact=round(delta_cost, 2),
                annual_impact=round(delta_cost * 12, 2),
                confidence="high" if z >= 3.0 else "medium",
                why=(
                    f"{category} cost/revenue ratio rose to {ratio:.1%} in {month} "
                    f"vs prior avg {hist_mean:.1%} "
                    f"(+{rel_jump:.0%} ratio increase; z={z:.2f})"
                ),
                action=(
                    f"Renegotiate {category}: now {curr_pct}% of revenue, "
                    f"up from {prior_pct}%."
                ),
            ))
    return findings
