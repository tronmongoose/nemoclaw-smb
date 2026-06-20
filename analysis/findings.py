"""findings.py — Advisory finding generation from transactions and vendor graph.

Pure logic; no LLM.

Exports: Finding, find

Finding schema:
    title (str): short human-readable label
    category (str): expense category the finding relates to
    monthly_impact (float): estimated monthly $ impact
    annual_impact (float): estimated annual $ impact
    confidence (str): "high" | "medium" | "low"
    why (str): one-sentence explanation

find() produces ranked advisory findings:
    1. Expense anomalies (z-score via gbrain.anomaly_detector.scan)
       Revenue-correlated categories use ratio-to-revenue z-score, not absolute.
    2. Recurring-bill month-over-month jumps > alert_delta_pct
    3. Likely-duplicate or forgotten recurring charges
    4. Top recurring vendors by annualized cost (informational, low confidence)

Revenue-aware suppression (see revenue_correlation.py):
    Categories matched by config substring list OR auto-detected via Pearson r >= 0.7
    are scored on cost/revenue ratio, not absolute amount. A constant-% fee that rises
    with revenue produces no finding. A ratio that actually climbs fires a finding whose
    'why' cites the percentage change, not the dollar change.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from analysis.revenue_correlation import (
    DEFAULT_CORR_THRESHOLD,
    DEFAULT_CORRELATED_SUBSTRINGS,
    DEFAULT_RATIO_JUMP_THRESHOLD,
    DEFAULT_RATIO_Z_THRESHOLD,
    build_correlated_categories,
    ratio_findings_for_category,
    revenue_by_month as _revenue_by_month,
)

if TYPE_CHECKING:
    from gbrain.knowledge_graph import KnowledgeGraph


@dataclass
class Finding:
    """A single advisory finding with $ impact and confidence."""

    title: str
    category: str
    monthly_impact: float
    annual_impact: float
    confidence: str   # "high" | "medium" | "low"
    why: str


def _expense_anomaly_findings(
    transactions: list[dict[str, Any]],
    correlated_categories: frozenset[str],
    rev_by_month: dict[str, float],
    ratio_z_threshold: float,
    ratio_jump_threshold: float,
) -> list[Finding]:
    """Return findings for anomalous expenses.

    Revenue-correlated categories get ratio-based detection.
    Fixed-cost categories use the existing absolute z-score via anomaly_detector.
    """
    from gbrain.anomaly_detector import scan

    expenses = [t for t in transactions if t.get("direction") == "expense"]

    # Fixed-cost path: exclude transactions whose category is revenue-correlated
    fixed_expenses = [
        t for t in expenses
        if t.get("category", "") not in correlated_categories
    ]
    anomalies = scan(fixed_expenses)
    findings: list[Finding] = []
    for a in anomalies:
        delta = a.current_amount - a.baseline_mean
        findings.append(Finding(
            title=f"Expense spike: {a.vendor}",
            category=_vendor_category(a.vendor, expenses),
            monthly_impact=round(delta, 2),
            annual_impact=round(delta * 12, 2),
            confidence="high" if abs(a.z_score) >= 3.0 else "medium",
            why=a.reason,
        ))

    # Revenue-correlated path: ratio-based detection per category
    for cat in correlated_categories:
        findings.extend(
            ratio_findings_for_category(
                cat, expenses, rev_by_month,
                ratio_z_threshold, ratio_jump_threshold,
            )
        )

    return findings


def _recurring_jump_findings(
    transactions: list[dict[str, Any]],
    alert_delta_pct: float,
) -> list[Finding]:
    """Flag recurring vendors whose month-over-month charge grew > alert_delta_pct."""
    from gbrain.invoice_ingestion import detect_recurring

    expenses = [t for t in transactions if t.get("direction") == "expense"]
    recurring = detect_recurring(expenses)

    by_vendor_month: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for t in expenses:
        vendor = t.get("vendor", "")
        month = t.get("date", "")[:7]
        by_vendor_month[vendor][month].append(float(t.get("amount", 0.0)))

    recurring_vendors = {r["vendor"] for r in recurring}
    findings: list[Finding] = []

    for vendor in recurring_vendors:
        month_data = by_vendor_month.get(vendor, {})
        sorted_months = sorted(month_data.keys())
        if len(sorted_months) < 2:
            continue
        for i in range(1, len(sorted_months)):
            prev = sum(month_data[sorted_months[i - 1]])
            curr = sum(month_data[sorted_months[i]])
            if prev <= 0:
                continue
            pct = (curr - prev) / prev * 100
            if pct > alert_delta_pct:
                delta = curr - prev
                findings.append(Finding(
                    title=f"Recurring bill jump: {vendor}",
                    category=_vendor_category(vendor, expenses),
                    monthly_impact=round(delta, 2),
                    annual_impact=round(delta * 12, 2),
                    confidence="medium",
                    why=(
                        f"{vendor} charged ${curr:.2f} in {sorted_months[i]} vs "
                        f"${prev:.2f} in {sorted_months[i-1]} "
                        f"(+{pct:.0f}%, threshold {alert_delta_pct:.0f}%)"
                    ),
                ))

    return findings


def _duplicate_charge_findings(transactions: list[dict[str, Any]]) -> list[Finding]:
    """Flag vendors with multiple same-day charges of similar amount (likely duplicate)."""
    expenses = [t for t in transactions if t.get("direction") == "expense"]

    by_vendor_day: dict[tuple[str, str], list[float]] = defaultdict(list)
    for t in expenses:
        key = (t.get("vendor", ""), t.get("date", ""))
        by_vendor_day[key].append(float(t.get("amount", 0.0)))

    findings: list[Finding] = []
    for (vendor, day), amounts in by_vendor_day.items():
        if len(amounts) < 2:
            continue
        mean = statistics.mean(amounts)
        if all(abs(a - mean) / max(mean, 0.01) < 0.05 for a in amounts):
            total = sum(amounts)
            findings.append(Finding(
                title=f"Possible duplicate charge: {vendor}",
                category=_vendor_category(vendor, expenses),
                monthly_impact=round(total - mean, 2),
                annual_impact=round((total - mean) * 12, 2),
                confidence="medium",
                why=(
                    f"{len(amounts)} charges to {vendor} on {day} "
                    f"each ~${mean:.2f} — review for duplicate billing."
                ),
            ))
    return findings


def _top_recurring_findings(transactions: list[dict[str, Any]]) -> list[Finding]:
    """Return informational findings for the top 3 recurring vendors by annualized cost."""
    from gbrain.invoice_ingestion import detect_recurring

    expenses = [t for t in transactions if t.get("direction") == "expense"]
    recurring = detect_recurring(expenses)

    findings: list[Finding] = []
    for r in recurring[:3]:
        annual = round(r["monthly_cost"] * 12, 2)
        findings.append(Finding(
            title=f"Top recurring: {r['vendor']}",
            category=_vendor_category(r["vendor"], expenses),
            monthly_impact=round(r["monthly_cost"], 2),
            annual_impact=annual,
            confidence="low",
            why=(
                f"{r['vendor']} is a {r['frequency']} charge averaging "
                f"${r['amount']:.2f} ({r['occurrences']} occurrences, "
                f"${annual:.0f}/yr annualized)."
            ),
        ))
    return findings


def _vendor_category(vendor: str, transactions: list[dict[str, Any]]) -> str:
    """Return the most common category for a vendor in the transaction list."""
    cats: list[str] = [
        t.get("category", "Other") or "Other"
        for t in transactions
        if t.get("vendor") == vendor
    ]
    if not cats:
        return "Other"
    return max(set(cats), key=cats.count)


def find(
    transactions: list[dict[str, Any]],
    graph: "KnowledgeGraph",  # noqa: ARG001 — reserved for future graph-based logic
    thresholds: dict[str, Any],
) -> list[Finding]:
    """Produce ranked advisory findings from transactions and thresholds.

    Ranking: anomalies (high confidence) first, then jumps, duplicates, informational.
    graph is accepted for API completeness; future use for vendor-history cross-check.

    thresholds keys (all optional):
        alert_delta_pct (float): MoM recurring-jump % threshold. Default 20.
        revenue_correlated (list[str]): additional category names to treat as
            revenue-correlated (added to the default substring-match set).
        corr_threshold (float): Pearson r floor for auto-detection. Default 0.7.
        ratio_z_threshold (float): z-score threshold for ratio anomaly. Default 2.0.
        ratio_jump_threshold (float): relative ratio rise threshold. Default 0.30.
    """
    alert_delta_pct = float(thresholds.get("alert_delta_pct", 20.0))
    corr_threshold = float(thresholds.get("corr_threshold", DEFAULT_CORR_THRESHOLD))
    ratio_z_threshold = float(thresholds.get("ratio_z_threshold", DEFAULT_RATIO_Z_THRESHOLD))
    ratio_jump_threshold = float(thresholds.get("ratio_jump_threshold", DEFAULT_RATIO_JUMP_THRESHOLD))

    extra_correlated: list[str] = thresholds.get("revenue_correlated", [])
    config_substrings = DEFAULT_CORRELATED_SUBSTRINGS + tuple(
        s.lower() for s in extra_correlated
    )

    expenses = [t for t in transactions if t.get("direction") == "expense"]
    rev_by_month = _revenue_by_month(transactions)

    correlated_categories = build_correlated_categories(
        expenses, rev_by_month, config_substrings, corr_threshold,
    )

    all_findings: list[Finding] = []
    all_findings.extend(
        _expense_anomaly_findings(
            transactions, correlated_categories, rev_by_month,
            ratio_z_threshold, ratio_jump_threshold,
        )
    )
    all_findings.extend(_recurring_jump_findings(transactions, alert_delta_pct))
    all_findings.extend(_duplicate_charge_findings(transactions))
    all_findings.extend(_top_recurring_findings(transactions))

    _CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda f: (
        _CONFIDENCE_ORDER.get(f.confidence, 3),
        -f.annual_impact,
    ))
    return all_findings
