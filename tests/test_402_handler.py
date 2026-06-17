"""Tests for payments/payment_402_handler.py.

aws_renewal_402 -> outcome "paid" with payment + ledger.
adobe_anomaly_402 -> outcome "escalated" with anomaly + approval_request_id.
Audit chain valid after each call.

All audit and approval state is isolated per test via tmp_path + monkeypatch.
"""

import pytest

from agent.audit_log import verify_chain
from fixtures.seed_data import adobe_anomaly_402, aws_renewal_402, seed_invoices
from gbrain.knowledge_graph import build_graph_from_invoices
from payments.payment_402_handler import handle_402


@pytest.fixture()
def audit_path(tmp_path):
    """Return a per-test audit JSONL path inside tmp_path."""
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
    """KnowledgeGraph populated with 5 months of seed history (no June anomaly entry)."""
    # Exclude the last record (June Adobe anomaly) so history is clean before the event.
    invoices = seed_invoices()
    # Last entry is the June Adobe spike; strip it for a clean baseline.
    baseline = [inv for inv in invoices if inv["date"] < "2026-06-01"]
    return build_graph_from_invoices(baseline)


@pytest.fixture(autouse=True)
def clear_c1_api_key(monkeypatch):
    monkeypatch.delenv("C1_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# AWS renewal -> auto-paid
# ---------------------------------------------------------------------------

def test_aws_renewal_outcome_paid(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["outcome"] == "paid"


def test_aws_renewal_has_payment(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["payment"] is not None
    assert result["payment"]["status"] == "succeeded"


def test_aws_renewal_has_ledger_entry(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["ledger_entry"] is not None
    assert result["ledger_entry"]["status"] == "posted"


def test_aws_renewal_no_approval_request(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["approval_request_id"] is None


def test_aws_renewal_audit_chain_valid(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    ok, msg = verify_chain(audit_path)
    assert ok, msg


def test_aws_renewal_has_audit_entry_hash(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["audit_entry_hash"] is not None
    assert len(result["audit_entry_hash"]) == 64  # sha256 hex


# ---------------------------------------------------------------------------
# Adobe anomaly -> escalated
# ---------------------------------------------------------------------------

def test_adobe_anomaly_outcome_escalated(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["outcome"] == "escalated"


def test_adobe_anomaly_has_approval_request_id(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["approval_request_id"] is not None
    assert isinstance(result["approval_request_id"], str)


def test_adobe_anomaly_has_anomaly_dict(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["anomaly"] is not None
    assert result["anomaly"]["is_anomaly"] is True


def test_adobe_anomaly_no_payment(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["payment"] is None


def test_adobe_anomaly_audit_chain_valid(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    ok, msg = verify_chain(audit_path)
    assert ok, msg


def test_adobe_anomaly_has_audit_entry_hash(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    assert result["audit_entry_hash"] is not None


# ---------------------------------------------------------------------------
# Steps shape
# ---------------------------------------------------------------------------

def test_aws_renewal_steps_include_required_keys(graph, audit_path, approvals_dir):
    event = aws_renewal_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    step_names = {s["step"] for s in result["steps"]}
    assert "gbrain_lookup" in step_names
    assert "policy_check" in step_names
    assert "anomaly_score" in step_names
    assert "payment" in step_names


def test_adobe_anomaly_steps_include_escalation(graph, audit_path, approvals_dir):
    event = adobe_anomaly_402()
    result = handle_402(event, graph, threshold=500.0, audit_path=audit_path)
    step_names = {s["step"] for s in result["steps"]}
    assert "escalation" in step_names
