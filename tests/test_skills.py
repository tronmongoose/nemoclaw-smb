"""
test_skills.py — Registry and skill-behavior tests for the NeMo Agent Toolkit skills layer.

No live network; anomaly_detect_skill with_reasoning=False, vendor_analyze_skill uses mock offline.
"""

import pytest

import agent.skills as skills_module
from agent.skills.base import Skill, to_nat_function
from fixtures.seed_data import affinity_alternative, seed_invoices


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------

_EXPECTED_SKILLS = {
    "access_governance_skill",
    "onboarding_skill",
    "invoice_ingest_skill",
    "anomaly_detect_skill",
    "vendor_analyze_skill",
    "handle_402_skill",
    "approval_gate_skill",
    "audit_skill",
}


def test_registry_count():
    """Registry contains exactly 8 skills."""
    assert len(skills_module.all_skills()) == 8


def test_registry_names_match():
    """all_skills_names() returns the exact expected set of 8 skill names."""
    assert set(skills_module.all_skills_names()) == _EXPECTED_SKILLS


def test_get_returns_skill():
    """get() returns a Skill instance for every registered name."""
    for name in _EXPECTED_SKILLS:
        s = skills_module.get(name)
        assert isinstance(s, Skill)
        assert s.name == name


def test_get_unknown_raises():
    """get() raises KeyError for an unregistered name."""
    with pytest.raises(KeyError):
        skills_module.get("not_a_real_skill")


# ---------------------------------------------------------------------------
# to_nat_function
# ---------------------------------------------------------------------------

def test_to_nat_function_shape():
    """to_nat_function() emits a dict with name and description."""
    skill = skills_module.get("onboarding_skill")
    nat = to_nat_function(skill)
    assert "name" in nat
    assert "description" in nat
    assert nat["name"] == "onboarding_skill"
    assert isinstance(nat["description"], str) and len(nat["description"]) > 0


# ---------------------------------------------------------------------------
# onboarding_skill
# ---------------------------------------------------------------------------

def test_onboarding_builds_graph_with_4_vendor_nodes():
    """onboarding_skill.run() builds a graph with exactly 4 vendor nodes from seed data."""
    result = skills_module.run_skill("onboarding_skill", {})
    assert result["vendor_count"] == 4
    vendor_names = {v.lower() for v in result["vendors"]}
    assert any("adobe" in v for v in vendor_names)
    assert any("figma" in v for v in vendor_names)
    assert any("aws" in v for v in vendor_names)
    assert any("gusto" in v for v in vendor_names)


# ---------------------------------------------------------------------------
# invoice_ingest_skill
# ---------------------------------------------------------------------------

def test_invoice_ingest_skill_produces_records():
    """invoice_ingest_skill returns graph records and detects recurring vendors."""
    invoices = seed_invoices()
    result = skills_module.run_skill("invoice_ingest_skill", {"invoices": invoices})
    assert result["graph_node_count"] == 4
    assert result["graph_edge_count"] == len(invoices)
    assert isinstance(result["recurring"], list)


# ---------------------------------------------------------------------------
# anomaly_detect_skill
# ---------------------------------------------------------------------------

def test_anomaly_detect_flags_adobe():
    """anomaly_detect_skill flags the Adobe $340 anomaly from seed invoices."""
    invoices = seed_invoices()
    flat = [{"vendor": inv["vendor"], "amount": inv["amount"], "date": inv["date"]}
            for inv in invoices]
    result = skills_module.run_skill("anomaly_detect_skill", {
        "invoices": flat,
        "with_reasoning": False,
    })
    assert result["anomaly_count"] >= 1
    flagged_vendors = {a["vendor"] for a in result["anomalies"]}
    assert any("adobe" in v.lower() for v in flagged_vendors)


def test_anomaly_detect_no_reasoning_key_when_disabled():
    """anomaly_detect_skill does not attach reasoning when with_reasoning=False."""
    invoices = seed_invoices()
    flat = [{"vendor": inv["vendor"], "amount": inv["amount"], "date": inv["date"]}
            for inv in invoices]
    result = skills_module.run_skill("anomaly_detect_skill", {
        "invoices": flat,
        "with_reasoning": False,
    })
    for anomaly in result["anomalies"]:
        assert "reasoning" not in anomaly


# ---------------------------------------------------------------------------
# vendor_analyze_skill
# ---------------------------------------------------------------------------

def test_vendor_analyze_returns_ranked_options():
    """vendor_analyze_skill returns ranked alternatives (reasoning may be mock offline)."""
    current = {"vendor": "Adobe Creative Cloud", "amount": 277.0, "frequency": "monthly"}
    alternatives = [affinity_alternative()]
    result = skills_module.run_skill("vendor_analyze_skill", {
        "current": current,
        "alternatives": alternatives,
        "context": {"note": "test"},
    })
    assert "ranked_alternatives" in result
    assert len(result["ranked_alternatives"]) == 1
    ranked = result["ranked_alternatives"][0]
    assert "monthly_savings" in ranked
    assert "annual_savings" in ranked
    assert ranked["rank"] == 1
    assert isinstance(result["reasoning"], str) and len(result["reasoning"]) > 0


# ---------------------------------------------------------------------------
# approval_gate_skill
# ---------------------------------------------------------------------------

def test_approval_gate_list_pending_returns_list():
    """approval_gate_skill list_pending action returns a list."""
    result = skills_module.run_skill("approval_gate_skill", {"action": "list_pending"})
    assert "pending" in result
    assert isinstance(result["pending"], list)


# ---------------------------------------------------------------------------
# audit_skill
# ---------------------------------------------------------------------------

def test_audit_skill_verify_chain():
    """audit_skill verify_chain returns ok=True when no audit file exists."""
    result = skills_module.run_skill("audit_skill", {
        "action": "verify_chain",
        "audit_path": "/tmp/nemoclaw_test_audit_nonexistent.jsonl",
    })
    assert result["ok"] is True


def test_audit_skill_recent_empty_when_no_file():
    """audit_skill recent returns empty list when audit file does not exist."""
    result = skills_module.run_skill("audit_skill", {
        "action": "recent",
        "audit_path": "/tmp/nemoclaw_test_audit_nonexistent.jsonl",
    })
    assert result["entries"] == []
    assert result["count"] == 0
