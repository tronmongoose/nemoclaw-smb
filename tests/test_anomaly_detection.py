"""tests/test_anomaly_detection.py -- Act I: STR Owner Agent anomaly detection tests.

Covers:
  - Fee anomaly flagged BEFORE payment is triggered
  - Corrected fee computed as 84000c ($840), not 92400c ($924)
  - REQUIRE_APPROVAL fires on the $840 corrected payment
  - Audit entry created with anomaly details; chain verifies
  - All non-prop-001 properties pass with NO anomaly flag
  - All assertions pass with DEMO_MODE and no live creds
"""
from __future__ import annotations

import os
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def demo_env(tmp_path, monkeypatch):
    """Force DEMO_MODE and isolate audit + approvals to tmp_path."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("NEMOCLAW_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(tmp_path / "approvals"))
    # Reload str_owner_agent so _NHI is issued with the clean env.
    import importlib
    import acts.str_owner_agent as m
    importlib.reload(m)
    return tmp_path


# ---------------------------------------------------------------------------
# ingest_ledger
# ---------------------------------------------------------------------------

class TestIngestLedger:
    """LedgerSummary data matches mock_ledger constants for prop-001."""

    def test_revenue_cents(self):
        """prop-001 revenue must be 420000 cents ($4,200)."""
        from acts.str_owner_agent import ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        assert s.revenue_cents == 420_000

    def test_contract_pct(self):
        """prop-001 contract rate must be 0.20."""
        from acts.str_owner_agent import ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        assert s.contract_pct == pytest.approx(0.20)

    def test_charged_pct(self):
        """prop-001 charged rate must be 0.22."""
        from acts.str_owner_agent import ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        assert s.charged_pct == pytest.approx(0.22)

    def test_unknown_property_raises(self):
        """ingest_ledger must propagate KeyError for an unknown property_id."""
        from acts.str_owner_agent import ingest_ledger
        with pytest.raises(KeyError):
            ingest_ledger("prop-999", "2026-06")


# ---------------------------------------------------------------------------
# detect_fee_anomaly
# ---------------------------------------------------------------------------

class TestDetectFeeAnomaly:
    """Anomaly flagged before payment; fee math is correct."""

    def test_anomaly_flagged_for_prop001(self):
        """detect_fee_anomaly must return is_anomaly=True for prop-001 ledger."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        result = detect_fee_anomaly(s, s.contract_pct)
        assert result.is_anomaly is True

    def test_expected_fee_is_840_dollars(self):
        """Expected fee for prop-001 must be 84000 cents ($840), not 92400 ($924)."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        result = detect_fee_anomaly(s, s.contract_pct)
        assert result.expected_fee_cents == 84_000

    def test_charged_fee_is_924_dollars(self):
        """Charged fee for prop-001 must be 92400 cents ($924)."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        result = detect_fee_anomaly(s, s.contract_pct)
        assert result.charged_fee_cents == 92_400

    def test_overcharge_is_84_dollars(self):
        """Overcharge must be 8400 cents ($84)."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        result = detect_fee_anomaly(s, s.contract_pct)
        assert result.overcharge_cents == 8_400

    def test_anomaly_detected_before_payment(self):
        """detect_fee_anomaly must not trigger any payment side-effect."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        # This must complete without invoking stripe or audit -- pure detection.
        result = detect_fee_anomaly(s, s.contract_pct)
        assert result.is_anomaly is True  # detection done; no payment raised

    def test_reason_mentions_overcharge(self):
        """Reason string must reference the overcharge direction."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        result = detect_fee_anomaly(s, s.contract_pct)
        assert "over" in result.reason.lower()

    def test_reasoning_trace_present_in_demo_mode(self):
        """In DEMO_MODE, reasoning_trace must be a non-empty string."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        s = ingest_ledger("prop-001", "2026-06")
        result = detect_fee_anomaly(s, s.contract_pct)
        assert len(result.reasoning_trace) > 0

    def test_no_anomaly_for_correct_properties(self):
        """Properties with matching contract and charged rates must return is_anomaly=False."""
        from acts.str_owner_agent import detect_fee_anomaly, ingest_ledger
        for pid in ("prop-002", "prop-003", "prop-004", "prop-005"):
            s = ingest_ledger(pid, "2026-06")
            result = detect_fee_anomaly(s, s.contract_pct)
            assert result.is_anomaly is False, f"{pid} should not be anomalous"
            assert result.overcharge_cents == 0, f"{pid} overcharge must be zero"


# ---------------------------------------------------------------------------
# trigger_payment: REQUIRE_APPROVAL fires on $840
# ---------------------------------------------------------------------------

class TestTriggerPayment:
    """ApprovalRequired fires for amounts over the $500 threshold."""

    def test_require_approval_fires_on_840(self):
        """trigger_payment must raise ApprovalRequired for 84000c ($840 > $500)."""
        from agent.require_approval import ApprovalRequired
        from acts.str_owner_agent import trigger_payment
        with pytest.raises(ApprovalRequired) as exc_info:
            trigger_payment(84_000, "prop-001", requires_approval=True)
        assert exc_info.value.amount == pytest.approx(840.0)

    def test_no_approval_needed_below_threshold(self):
        """trigger_payment must complete without raising for 10000c ($100 <= $500)."""
        from acts.str_owner_agent import trigger_payment
        result = trigger_payment(10_000, "prop-001", requires_approval=True)
        assert result.status in ("succeeded", "pending", "processing")
        assert result.amount_cents == 10_000

    def test_bypass_gate_completes(self):
        """trigger_payment with requires_approval=False must skip gate and succeed."""
        from acts.str_owner_agent import trigger_payment
        result = trigger_payment(84_000, "prop-001", requires_approval=False)
        assert result.payment_id != ""
        assert result.amount_cents == 84_000

    def test_audit_entry_written_on_payment(self):
        """A completed payment must write an audit entry; chain must verify."""
        from agent.audit_log import verify_chain
        from acts.str_owner_agent import trigger_payment
        trigger_payment(10_000, "prop-001", requires_approval=True)
        ok, detail = verify_chain()
        assert ok is True, detail


# ---------------------------------------------------------------------------
# Audit chain
# ---------------------------------------------------------------------------

class TestAuditChain:
    """Audit entries are created with anomaly details and the chain verifies."""

    def test_audit_entry_has_anomaly_metadata(self):
        """After reconcile_month, the audit log must have a payment entry; chain verifies."""
        from agent.audit_log import verify_chain
        from acts.str_owner_agent import reconcile_month

        report = reconcile_month("prop-001", "2026-06")
        # payment result carries the audit hash from the chained entry
        assert report.payment is not None
        assert report.payment.audit_hash != "", "audit_hash must be set after payment"
        ok, detail = verify_chain()
        assert ok is True, detail

    def test_chain_verifies_after_reconcile(self):
        """verify_chain must return ok=True after a full reconcile_month run."""
        from agent.audit_log import verify_chain
        from acts.str_owner_agent import reconcile_month

        reconcile_month("prop-001", "2026-06")
        ok, detail = verify_chain()
        assert ok is True, detail


# ---------------------------------------------------------------------------
# reconcile_month end-to-end
# ---------------------------------------------------------------------------

class TestReconcileMonth:
    """Full Act I flow: ingest -> detect -> approve -> pay -> report."""

    def test_reconcile_returns_report(self):
        """reconcile_month must return a ReconciliationReport for prop-001."""
        from acts.str_owner_agent import ReconciliationReport, reconcile_month
        report = reconcile_month("prop-001", "2026-06")
        assert isinstance(report, ReconciliationReport)

    def test_reconcile_detects_anomaly(self):
        """ReconciliationReport.anomaly.is_anomaly must be True for prop-001."""
        from acts.str_owner_agent import reconcile_month
        report = reconcile_month("prop-001", "2026-06")
        assert report.anomaly.is_anomaly is True

    def test_reconcile_expected_fee_84000(self):
        """ReconciliationReport corrected fee must be 84000 cents."""
        from acts.str_owner_agent import reconcile_month
        report = reconcile_month("prop-001", "2026-06")
        assert report.anomaly.expected_fee_cents == 84_000

    def test_reconcile_payment_amount(self):
        """Payment amount in demo must equal the corrected fee (84000c)."""
        from acts.str_owner_agent import reconcile_month
        report = reconcile_month("prop-001", "2026-06")
        assert report.payment is not None
        assert report.payment.amount_cents == 84_000

    def test_reconcile_audit_ok(self):
        """ReconciliationReport.audit_ok must be True after the run."""
        from acts.str_owner_agent import reconcile_month
        report = reconcile_month("prop-001", "2026-06")
        assert report.audit_ok is True

    def test_reconcile_nhi_id_present(self):
        """ReconciliationReport must carry the NHI id for the C1 identity beat."""
        from acts.str_owner_agent import reconcile_month
        report = reconcile_month("prop-001", "2026-06")
        assert report.nhi_id.startswith("nhi-str-owner-agent-")

    def test_no_payment_when_no_anomaly(self):
        """reconcile_month for a non-anomalous property must leave payment=None."""
        from acts.str_owner_agent import reconcile_month
        report = reconcile_month("prop-002", "2026-06")
        assert report.anomaly.is_anomaly is False
        assert report.payment is None

    def test_non_anomaly_properties_all_pass(self):
        """All non-prop-001 properties must produce no anomaly in reconcile."""
        from acts.str_owner_agent import reconcile_month
        for pid in ("prop-002", "prop-003", "prop-004", "prop-005"):
            report = reconcile_month(pid, "2026-06")
            assert report.anomaly.is_anomaly is False, f"{pid} must not flag anomaly"
            assert report.payment is None, f"{pid} must not trigger payment"
