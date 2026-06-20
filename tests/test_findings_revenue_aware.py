"""test_findings_revenue_aware.py — Offline tests for revenue-aware anomaly suppression.

Covers:
- Constant-ratio correlated cost produces NO expense-spike finding (bug regression)
- Rising ratio (manager raised cut) DOES fire, with ratio-pct in 'why'
- Fixed-cost real spike (utility doubling) still fires (no regression)
- Auto-detect: unlisted category strongly correlated with revenue is treated as correlated
- Helpers: _pearson_r edge cases, _is_config_correlated substrings
"""

from __future__ import annotations

import pytest

from analysis.findings import Finding, find
from analysis.revenue_correlation import (
    pearson_r as _pearson_r,
    is_config_correlated as _is_config_correlated,
    DEFAULT_CORRELATED_SUBSTRINGS as _DEFAULT_CORRELATED_SUBSTRINGS,
)
from gbrain.knowledge_graph import KnowledgeGraph


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

def test_pearson_r_perfect_positive():
    """Perfectly correlated sequences return r=1.0."""
    xs = [1.0, 2.0, 3.0, 4.0]
    assert _pearson_r(xs, xs) == pytest.approx(1.0)


def test_pearson_r_perfect_negative():
    """Perfectly anti-correlated sequences return r=-1.0."""
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [4.0, 3.0, 2.0, 1.0]
    assert _pearson_r(xs, ys) == pytest.approx(-1.0)


def test_pearson_r_degenerate_constant():
    """Zero std-dev (constant series) returns 0.0 without error."""
    assert _pearson_r([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) == 0.0


def test_pearson_r_too_short():
    """Single-element sequences return 0.0."""
    assert _pearson_r([1.0], [2.0]) == 0.0


def test_config_correlated_mgmt():
    """'mgmt fees' matches the 'mgmt' default substring."""
    assert _is_config_correlated("mgmt fees", _DEFAULT_CORRELATED_SUBSTRINGS)


def test_config_correlated_cleaning():
    """'Cleaning Service' matches 'cleaning' (case-insensitive)."""
    assert _is_config_correlated("Cleaning Service", _DEFAULT_CORRELATED_SUBSTRINGS)


def test_config_correlated_fixed_utility():
    """'utilities' does NOT match any default correlated substring."""
    assert not _is_config_correlated("utilities", _DEFAULT_CORRELATED_SUBSTRINGS)


# ---------------------------------------------------------------------------
# Synthetic transaction builders
# ---------------------------------------------------------------------------

def _months(n: int) -> list[str]:
    """Return n month strings starting 2025-01."""
    result = []
    for i in range(n):
        y, m = divmod(i, 12)
        result.append(f"{2025 + y}-{m + 1:02d}")
    return result


def _make_str_pnl(
    revenue_series: list[float],
    mgmt_ratio: float = 0.15,
    water_amounts: list[float] | None = None,
) -> list[dict]:
    """Build synthetic STR P&L transactions.

    mgmt fees = mgmt_ratio * revenue each month.
    water_amounts optional; defaults to $50/month flat.
    """
    months = _months(len(revenue_series))
    txns: list[dict] = []

    for i, (month, rev) in enumerate(zip(months, revenue_series)):
        # Income
        txns.append({
            "date": f"{month}-01",
            "vendor": "Rental Platform",
            "amount": rev,
            "direction": "income",
            "category": "rental_income",
        })
        # Mgmt fee (revenue-correlated, default substring match via 'mgmt')
        fee = rev * mgmt_ratio
        txns.append({
            "date": f"{month}-05",
            "vendor": "PM Company",
            "amount": fee,
            "direction": "expense",
            "category": "mgmt fees",
        })
        # Water (fixed cost)
        water = (water_amounts[i] if water_amounts else 50.0)
        txns.append({
            "date": f"{month}-10",
            "vendor": "Water Utility",
            "amount": water,
            "direction": "expense",
            "category": "utilities",
        })

    return txns


# ---------------------------------------------------------------------------
# Core regression: constant ratio → no finding
# ---------------------------------------------------------------------------

def test_constant_ratio_mgmt_no_spike_finding():
    """Mgmt fees at a constant 15% of revenue produce NO expense-spike finding.

    Revenue varies 2x across months; absolute fee amount doubles in high months.
    This is the bug: prior code treated those as anomalies.
    """
    # Revenue swings: low / high alternating, 6 months
    revenue = [2000.0, 4000.0, 2000.0, 4000.0, 2000.0, 4000.0]
    txns = _make_str_pnl(revenue, mgmt_ratio=0.15)
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    spike_titles = [
        f.title for f in findings
        if "spike" in f.title.lower() and "mgmt" in f.title.lower()
    ]
    assert spike_titles == [], (
        f"False-positive spike findings for constant-ratio mgmt fees: {spike_titles}"
    )


def test_constant_ratio_no_finding_even_with_2x_revenue_swing():
    """A 2x revenue swing with constant ratio is pure seasonality — zero findings for that category."""
    revenue = [1000.0, 3000.0, 1000.0, 3000.0, 1000.0, 3000.0]
    txns = _make_str_pnl(revenue, mgmt_ratio=0.20)
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    mgmt_spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "mgmt" in f.category.lower()
    ]
    assert mgmt_spikes == []


# ---------------------------------------------------------------------------
# Rising ratio → finding fires, why cites percentage
# ---------------------------------------------------------------------------

def test_rising_ratio_fires_finding():
    """Mgmt fee ratio rising from 15% to 25% triggers a finding."""
    # 6 months stable at 15%, then 25% in the last two months
    revenue = [3000.0, 3000.0, 3000.0, 3000.0, 3000.0, 3000.0]
    months = _months(6)
    txns: list[dict] = []
    for i, (month, rev) in enumerate(zip(months, revenue)):
        txns.append({
            "date": f"{month}-01",
            "vendor": "Rental Platform",
            "amount": rev,
            "direction": "income",
            "category": "rental_income",
        })
        ratio = 0.25 if i >= 4 else 0.15
        txns.append({
            "date": f"{month}-05",
            "vendor": "PM Company",
            "amount": rev * ratio,
            "direction": "expense",
            "category": "mgmt fees",
        })

    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    mgmt_spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "mgmt" in f.title.lower()
    ]
    assert len(mgmt_spikes) >= 1, f"Expected a ratio-based finding; got: {[f.title for f in findings]}"


def test_rising_ratio_why_cites_percentage():
    """The finding's 'why' field references the ratio/percentage, not just dollar amount."""
    revenue = [3000.0, 3000.0, 3000.0, 3000.0, 3000.0, 3000.0]
    months = _months(6)
    txns: list[dict] = []
    for i, (month, rev) in enumerate(zip(months, revenue)):
        txns.append({
            "date": f"{month}-01",
            "vendor": "Rental Platform",
            "amount": rev,
            "direction": "income",
            "category": "rental_income",
        })
        ratio = 0.25 if i >= 4 else 0.15
        txns.append({
            "date": f"{month}-05",
            "vendor": "PM Company",
            "amount": rev * ratio,
            "direction": "expense",
            "category": "mgmt fees",
        })

    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    mgmt_spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "mgmt" in f.title.lower()
    ]
    assert mgmt_spikes, "Expected at least one mgmt spike finding"
    why = mgmt_spikes[0].why
    # Why must mention ratio/percentage, not just a raw dollar figure
    assert "%" in why, f"Expected ratio/% in 'why'; got: {why}"


# ---------------------------------------------------------------------------
# Fixed-cost regression: Water-type absolute spike still fires
# ---------------------------------------------------------------------------

def test_fixed_cost_spike_still_fires():
    """A utility (fixed cost) doubling in one month still produces a spike finding."""
    water = [50.0, 52.0, 48.0, 51.0, 50.0, 124.0]  # month 6: 124% spike
    revenue = [3000.0] * 6
    txns = _make_str_pnl(revenue, water_amounts=water)
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    water_spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "water" in f.title.lower()
    ]
    assert len(water_spikes) >= 1, (
        f"Expected Water Utility spike to fire; got: {[f.title for f in findings]}"
    )


def test_fixed_cost_spike_positive_impact():
    """Fixed-cost spike finding has a positive monthly_impact (cost went up)."""
    water = [50.0, 52.0, 48.0, 51.0, 50.0, 124.0]
    revenue = [3000.0] * 6
    txns = _make_str_pnl(revenue, water_amounts=water)
    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    water_spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "water" in f.title.lower()
    ]
    assert water_spikes[0].monthly_impact > 0


# ---------------------------------------------------------------------------
# Auto-detect: unlisted but correlated category is treated as revenue-correlated
# ---------------------------------------------------------------------------

def test_auto_detect_correlated_category_suppressed():
    """An unlisted category (e.g. 'owner_draw') that correlates with revenue is suppressed.

    Auto-detect requires >= 4 shared months and Pearson r >= 0.7.
    """
    # 8 months; owner_draw = exactly 10% of revenue (r=1.0)
    revenue = [1000.0, 2000.0, 1500.0, 3000.0, 1000.0, 2500.0, 1800.0, 3000.0]
    months = _months(8)
    txns: list[dict] = []
    for month, rev in zip(months, revenue):
        txns.append({
            "date": f"{month}-01",
            "vendor": "Rental Platform",
            "amount": rev,
            "direction": "income",
            "category": "rental_income",
        })
        txns.append({
            "date": f"{month}-05",
            "vendor": "Owner Draw Co",
            "amount": rev * 0.10,
            "direction": "expense",
            "category": "owner_draw",   # NOT in default substrings
        })

    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "owner" in f.title.lower()
    ]
    assert spikes == [], (
        f"Auto-detect should suppress owner_draw (r=1.0 with revenue); got: {spikes}"
    )


def test_auto_detect_uncorrelated_category_not_suppressed():
    """A category uncorrelated with revenue is NOT auto-detected and keeps absolute detection.

    Uses slight variance in the base amounts so pstdev > 0 and z-score fires.
    A perfectly flat history yields pstdev=0 (z undefined); this test uses realistic
    slight variation so the spike is detectable by the existing absolute detector.
    """
    # Revenue alternates strongly; internet is flat-ish (anti-correlated; r < 0.7)
    revenue = [1000.0, 3000.0, 1000.0, 3000.0, 1000.0, 3000.0, 1000.0, 3000.0]
    # Internet costs: slight variation so pstdev > 0; last entry is a real spike
    internet_costs = [58.0, 62.0, 59.0, 61.0, 60.0, 63.0, 57.0, 200.0]
    months = _months(8)
    txns: list[dict] = []
    for month, rev, inet in zip(months, revenue, internet_costs):
        txns.append({
            "date": f"{month}-01",
            "vendor": "Rental Platform",
            "amount": rev,
            "direction": "income",
            "category": "rental_income",
        })
        txns.append({
            "date": f"{month}-05",
            "vendor": "Internet Co",
            "amount": inet,
            "direction": "expense",
            "category": "internet",
        })

    graph = KnowledgeGraph()
    findings = find(txns, graph, {"alert_delta_pct": 20.0})

    # Internet should still be detectable by absolute z-score (not suppressed as correlated)
    internet_spikes = [
        f for f in findings
        if "spike" in f.title.lower() and "internet" in f.title.lower()
    ]
    assert len(internet_spikes) >= 1, (
        f"Uncorrelated category should use absolute detection; got: {[f.title for f in findings]}"
    )
