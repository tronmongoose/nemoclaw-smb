"""test_v2_dashboard.py — Offline tests for v2 analysis.json schema and findings upgrades.

Covers:
- Finding.action is populated for each finding type (expense spike, recurring jump,
  duplicate charge, top recurring)
- Findings are ranked by annual_impact desc
- analysis.json v2 top-level keys: headlines, longitudinal
- headlines <= 3, each with non-empty series, action, severity
- longitudinal.net_by_month spans all loaded months
- longitudinal.by_category_monthly has one entry per expense category with series
- Multi-year fixture (2024+2025) produces months from both years in correct order
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.export import (
    write_analysis_json,
    _net_by_month,
    _category_monthly_series,
)
from analysis.findings import Finding, find
from analysis.pnl import compute_pnl
from agent.tenancy import Tenant
from gbrain.knowledge_graph import KnowledgeGraph


# ---------------------------------------------------------------------------
# Shared synthetic helpers
# ---------------------------------------------------------------------------

def _make_tenant(tmp_path: Path) -> Tenant:
    """Return a synthetic Tenant rooted in tmp_path."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    return Tenant(
        slug="_sample_str",
        data_root=str(data_root),
        llm_routing="local",
        sensitivity="restricted",
        mode="advisory",
    )


def _multi_year_transactions() -> list[dict]:
    """Two years of synthetic STR transactions (2024 + 2025)."""
    txns = []
    for year in (2024, 2025):
        rev_base = 2800.0 if year == 2024 else 3000.0
        for month in range(1, 7):
            ym = f"{year}-{month:02d}"
            txns.append({
                "date": f"{ym}-05", "vendor": "STR Rental Income",
                "amount": rev_base + month * 200.0,
                "direction": "income", "category": "rental_income",
            })
            txns.append({
                "date": f"{ym}-08", "vendor": "Electric Co",
                "amount": 95.0 + month * 5.0,
                "direction": "expense", "category": "utilities",
            })
            txns.append({
                "date": f"{ym}-10", "vendor": "Cleaning Crew LLC",
                "amount": 220.0,
                "direction": "expense", "category": "maintenance",
            })
    return txns


def _recurring_jump_txns() -> list[dict]:
    """Lawn vendor jumps > 20% in month 3; Ring Security is stable."""
    return [
        {"date": "2025-01-14", "vendor": "Lawn Care Pro", "amount": 80.0,
         "direction": "expense", "category": "lawn"},
        {"date": "2025-02-14", "vendor": "Lawn Care Pro", "amount": 82.0,
         "direction": "expense", "category": "lawn"},
        {"date": "2025-03-14", "vendor": "Lawn Care Pro", "amount": 110.0,
         "direction": "expense", "category": "lawn"},
        {"date": "2025-01-01", "vendor": "Ring Security", "amount": 9.99,
         "direction": "expense", "category": "security"},
        {"date": "2025-02-01", "vendor": "Ring Security", "amount": 9.99,
         "direction": "expense", "category": "security"},
        {"date": "2025-03-01", "vendor": "Ring Security", "amount": 9.99,
         "direction": "expense", "category": "security"},
    ]


def _anomaly_txns() -> list[dict]:
    """Electric Co spikes in month 6; history provides stable baseline."""
    amounts = [95.0, 100.0, 105.0, 98.0, 110.0, 180.0]
    return [
        {"date": f"2025-0{i}-01", "vendor": "Electric Co",
         "amount": amounts[i - 1],
         "direction": "expense", "category": "utilities"}
        for i in range(1, 7)
    ]


# ---------------------------------------------------------------------------
# Finding.action populated per type
# ---------------------------------------------------------------------------

class TestFindingAction:
    def test_anomaly_action_non_empty(self):
        """Expense spike finding carries a non-empty action."""
        txns = _anomaly_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        spike = next((f for f in findings if "spike" in f.title.lower()), None)
        assert spike is not None
        assert spike.action != "", "action must not be empty for expense spike"

    def test_anomaly_action_contains_category(self):
        """Expense spike action references the category."""
        txns = _anomaly_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        spike = next(f for f in findings if "spike" in f.title.lower())
        assert "utilities" in spike.action.lower()

    def test_recurring_jump_action_non_empty(self):
        """Recurring jump finding carries a non-empty action."""
        txns = _recurring_jump_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        jump = next((f for f in findings if "jump" in f.title.lower()), None)
        assert jump is not None
        assert jump.action != ""

    def test_recurring_jump_action_imperative(self):
        """Recurring jump action starts with 'Renegotiate' or 'Review'."""
        txns = _recurring_jump_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        jump = next(f for f in findings if "jump" in f.title.lower())
        assert jump.action.startswith(("Renegotiate", "Review"))

    def test_top_recurring_action_non_empty(self):
        """Top recurring finding carries a non-empty action."""
        txns = _recurring_jump_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        top = next((f for f in findings if "Top recurring" in f.title), None)
        assert top is not None
        assert top.action != ""


# ---------------------------------------------------------------------------
# Findings sorted by annual_impact desc
# ---------------------------------------------------------------------------

class TestFindingsRanking:
    def test_sorted_by_annual_impact_desc(self):
        """Findings list is sorted by annual_impact descending."""
        txns = _multi_year_transactions() + _recurring_jump_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        impacts = [f.annual_impact for f in findings]
        assert impacts == sorted(impacts, reverse=True), (
            f"Not sorted desc: {impacts}"
        )

    def test_highest_impact_is_first(self):
        """First finding has the highest annual_impact."""
        txns = _anomaly_txns()
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        if len(findings) >= 2:
            assert findings[0].annual_impact >= findings[1].annual_impact


# ---------------------------------------------------------------------------
# v2 analysis.json schema
# ---------------------------------------------------------------------------

class TestV2Schema:
    def test_top_level_keys_include_headlines_and_longitudinal(self, tmp_path):
        """v2 analysis.json has headlines and longitudinal at top level."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        write_analysis_json(tenant, pnl, findings, "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for key in ("tenant", "generated_at", "pnl", "headlines", "findings", "longitudinal"):
            assert key in doc, f"Missing v2 key: {key}"

    def test_headlines_max_three(self, tmp_path):
        """headlines contains at most 3 entries."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        write_analysis_json(tenant, pnl, findings, "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        assert len(doc["headlines"]) <= 3

    def test_headlines_have_required_keys(self, tmp_path):
        """Each headline has title, action, annual_impact, monthly_impact, severity, category, series."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions() + _recurring_jump_txns()
        pnl = compute_pnl(txns)
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        write_analysis_json(tenant, pnl, findings, "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for h in doc["headlines"]:
            for key in ("title", "action", "annual_impact", "monthly_impact",
                        "severity", "category", "series"):
                assert key in h, f"Headline missing key '{key}': {h}"

    def test_headlines_series_non_empty(self, tmp_path):
        """Each headline series has at least one entry."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions() + _recurring_jump_txns()
        pnl = compute_pnl(txns)
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        write_analysis_json(tenant, pnl, findings, "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for h in doc["headlines"]:
            assert len(h["series"]) > 0, f"Empty series for headline '{h['title']}'"

    def test_headlines_action_non_empty(self, tmp_path):
        """Each headline has a non-empty action string."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions() + _anomaly_txns()
        pnl = compute_pnl(txns)
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        write_analysis_json(tenant, pnl, findings, "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for h in doc["headlines"]:
            assert h["action"] != "", f"Empty action for headline '{h['title']}'"

    def test_findings_include_action_field(self, tmp_path):
        """Full findings list entries include action key."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        findings = find(txns, KnowledgeGraph(), {"alert_delta_pct": 20.0})
        write_analysis_json(tenant, pnl, findings, "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for f_item in doc["findings"]:
            assert "action" in f_item, f"Finding missing 'action': {f_item}"


# ---------------------------------------------------------------------------
# Longitudinal structure
# ---------------------------------------------------------------------------

class TestLongitudinal:
    def test_net_by_month_spans_all_months(self, tmp_path):
        """longitudinal.net_by_month has one entry per loaded month."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        write_analysis_json(tenant, pnl, [], "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        months = [e["month"] for e in doc["longitudinal"]["net_by_month"]]
        assert len(months) == len(pnl["monthly"]), (
            f"Expected {len(pnl['monthly'])} months, got {len(months)}"
        )

    def test_net_by_month_sorted_ascending(self, tmp_path):
        """longitudinal.net_by_month is sorted ascending by month."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        write_analysis_json(tenant, pnl, [], "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        months = [e["month"] for e in doc["longitudinal"]["net_by_month"]]
        assert months == sorted(months)

    def test_by_category_monthly_has_series_per_expense_category(self, tmp_path):
        """by_category_monthly has one entry per expense category."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        write_analysis_json(tenant, pnl, [], "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        entries = doc["longitudinal"]["by_category_monthly"]
        cats = [e["category"] for e in entries]
        assert "utilities" in cats
        assert "maintenance" in cats
        # income categories should NOT appear
        assert "rental_income" not in cats

    def test_by_category_series_length_matches_months(self, tmp_path):
        """Each category series has one entry per month (all months)."""
        tenant = _make_tenant(tmp_path)
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        total_months = len(pnl["monthly"])
        write_analysis_json(tenant, pnl, [], "2025-07-01T00:00:00+00:00")
        doc = json.loads((Path(tenant.data_root) / "analysis.json").read_text())
        for entry in doc["longitudinal"]["by_category_monthly"]:
            assert len(entry["series"]) == total_months, (
                f"Category {entry['category']} series length "
                f"{len(entry['series'])} != {total_months}"
            )


# ---------------------------------------------------------------------------
# Multi-year fixture: 2024 + 2025 months appear in order
# ---------------------------------------------------------------------------

class TestMultiYearFixture:
    def test_months_span_both_years(self):
        """Multi-year transactions produce months from 2024 and 2025."""
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        months = list(pnl["monthly"].keys())
        years = {m[:4] for m in months}
        assert "2024" in years, "Expected 2024 months in PNL"
        assert "2025" in years, "Expected 2025 months in PNL"

    def test_months_sorted_ascending_across_years(self):
        """Months from multi-year data are returned in ascending order."""
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        months = list(pnl["monthly"].keys())
        assert months == sorted(months)

    def test_net_by_month_helper_spans_both_years(self):
        """_net_by_month helper produces entries from both 2024 and 2025."""
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        net_months = [e["month"] for e in _net_by_month(pnl)]
        years = {m[:4] for m in net_months}
        assert "2024" in years
        assert "2025" in years

    def test_category_series_includes_all_years(self):
        """Per-category series includes months from both years."""
        txns = _multi_year_transactions()
        pnl = compute_pnl(txns)
        series_map = {
            e["category"]: [s["month"] for s in e["series"]]
            for e in _category_monthly_series(pnl)
        }
        assert "utilities" in series_map
        util_years = {m[:4] for m in series_map["utilities"]}
        assert "2024" in util_years
        assert "2025" in util_years
