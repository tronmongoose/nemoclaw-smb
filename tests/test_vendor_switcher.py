"""Tests for procurement/vendor_switcher.py.

switch_vendor(Adobe -> Affinity) returns 6 steps, outcome "switched",
monthly_savings > 0, and a valid audit chain.

All audit and approval state is isolated per test via tmp_path + monkeypatch.
The affinity_alternative fixture is annotated with old_monthly_equivalent
(~277/mo Adobe mean) so the savings computation is nonzero; this is the caller's
responsibility per the vendor_switcher docstring.
"""

import pytest

from agent.audit_log import verify_chain
from fixtures.seed_data import affinity_alternative, seed_invoices
from gbrain.knowledge_graph import build_graph_from_invoices
from procurement.vendor_switcher import switch_vendor

_ADOBE_MONTHLY_MEAN = 277.38  # mean of [275.50,277.00,276.80,278.20,277.40]


@pytest.fixture()
def audit_path(tmp_path):
    """Per-test audit JSONL path inside tmp_path."""
    return str(tmp_path / "audit.jsonl")


@pytest.fixture()
def approvals_dir(tmp_path, monkeypatch):
    """Redirect approval YAML writes to tmp_path."""
    d = tmp_path / "approvals"
    d.mkdir()
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(d))
    return str(d)


@pytest.fixture()
def graph():
    """KnowledgeGraph with 5 months of seed history (pre-June baseline)."""
    invoices = [inv for inv in seed_invoices() if inv["date"] < "2026-06-01"]
    return build_graph_from_invoices(invoices)


@pytest.fixture()
def annotated_affinity():
    """Affinity alternative annotated with Adobe's monthly cost for savings math."""
    alt = affinity_alternative()
    alt["old_monthly_equivalent"] = _ADOBE_MONTHLY_MEAN
    return alt


@pytest.fixture(autouse=True)
def clear_c1_api_key(monkeypatch):
    monkeypatch.delenv("C1_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# Core contract
# ---------------------------------------------------------------------------

def test_switch_outcome_is_switched(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert result["outcome"] == "switched"


def test_switch_returns_six_steps(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert len(result["steps"]) == 6


def test_switch_monthly_savings_positive(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert result["monthly_savings"] > 0


def test_switch_monthly_savings_reasonable(graph, annotated_affinity, audit_path, approvals_dir):
    # Adobe ~277/mo, Affinity 7.42/mo -> savings ~269/mo
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert result["monthly_savings"] > 200


def test_switch_audit_chain_valid(graph, annotated_affinity, audit_path, approvals_dir):
    switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    ok, msg = verify_chain(audit_path)
    assert ok, msg


def test_switch_has_audit_entry_hash(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert result["audit_entry_hash"] is not None
    assert len(result["audit_entry_hash"]) == 64


# ---------------------------------------------------------------------------
# Step names
# ---------------------------------------------------------------------------

def test_switch_step_names(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    names = [s["step"] for s in result["steps"]]
    assert names == [
        "policy_update",
        "stripe_cancel_old",
        "stripe_provision_new",
        "intuit_entry",
        "graph_update",
        "audit",
    ]


def test_switch_all_steps_ok_status(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    for step in result["steps"]:
        # "ok", "canceled", "active", "posted" are all success statuses in this mock
        assert step["status"] in {"ok", "canceled", "active", "posted"}


# ---------------------------------------------------------------------------
# Old/new vendor fields on result
# ---------------------------------------------------------------------------

def test_switch_result_has_old_vendor(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert result["old_vendor"] == "Adobe Creative Cloud"


def test_switch_result_has_new_vendor(graph, annotated_affinity, audit_path, approvals_dir):
    result = switch_vendor("Adobe Creative Cloud", annotated_affinity, graph, audit_path=audit_path)
    assert result["new_vendor"]["vendor"] == "Affinity Suite"
