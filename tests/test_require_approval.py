"""Tests for agent/require_approval.py.

Covers: auto-approve under threshold, ApprovalRequired over threshold,
decide()->approved flips is_approved, TTL expiry status, deterministic request_id.

All filesystem state isolated via monkeypatch on NEMOCLAW_APPROVALS_DIR.
TTL tests manipulate the stored record directly — no sleep required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from agent.require_approval import (
    ApprovalRequired,
    check,
    create_request,
    decide,
    enforce_spend,
    is_approved,
    list_pending,
    requires_approval,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def approvals_dir(tmp_path, monkeypatch):
    """Redirect approval YAML writes to a per-test temp directory."""
    d = tmp_path / "approvals"
    d.mkdir()
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(d))
    return d


# ---------------------------------------------------------------------------
# requires_approval
# ---------------------------------------------------------------------------

def test_under_threshold_returns_false(approvals_dir):
    """Amount at or below threshold does not require approval."""
    assert requires_approval("purchase", 50.0, threshold=100.0) is False


def test_over_threshold_returns_true(approvals_dir):
    """Amount strictly above threshold requires approval."""
    assert requires_approval("purchase", 150.0, threshold=100.0) is True


# ---------------------------------------------------------------------------
# enforce_spend — threshold param
# ---------------------------------------------------------------------------

def test_enforce_spend_under_threshold_auto_approves(approvals_dir):
    """enforce_spend returns auto-approved record when amount is under threshold."""
    result = enforce_spend("purchase", "AWS", 50.0, threshold=100.0)
    assert result["status"] == "auto-approved"


def test_enforce_spend_over_threshold_raises_approval_required(approvals_dir):
    """enforce_spend raises ApprovalRequired when amount exceeds supplied threshold."""
    with pytest.raises(ApprovalRequired):
        enforce_spend("purchase", "Gusto", 200.0, threshold=100.0)


def test_enforce_spend_approval_required_carries_request_id(approvals_dir):
    """Raised ApprovalRequired has a non-empty request_id."""
    with pytest.raises(ApprovalRequired) as exc_info:
        enforce_spend("purchase", "Figma", 500.0, threshold=100.0)
    assert exc_info.value.request_id


# ---------------------------------------------------------------------------
# decide -> is_approved
# ---------------------------------------------------------------------------

def test_decide_approved_flips_is_approved(approvals_dir):
    """After decide(..., approved=True), is_approved returns True."""
    rid = create_request("purchase", "Figma", 300.0, {})
    decide(rid, approved=True, decided_by="admin")
    assert is_approved(rid) is True


def test_decide_denied_keeps_is_approved_false(approvals_dir):
    """After decide(..., approved=False), is_approved returns False."""
    rid = create_request("purchase", "Figma", 300.0, {})
    decide(rid, approved=False, decided_by="admin")
    assert is_approved(rid) is False


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

def test_ttl_expiry_status(approvals_dir):
    """A record whose expires_at is in the past is auto-expired on check()."""
    rid = create_request("purchase", "Stripe", 200.0, {}, ttl_seconds=3600)
    path = approvals_dir / f"{rid}.yaml"
    record = yaml.safe_load(path.read_text())
    # Back-date the expiry so the record is already stale.
    record["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    path.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
    result = check(rid)
    assert result["status"] == "expired"


def test_expired_record_not_in_list_pending(approvals_dir):
    """Expired records must not appear in list_pending."""
    rid = create_request("purchase", "Stripe", 200.0, {}, ttl_seconds=3600)
    path = approvals_dir / f"{rid}.yaml"
    record = yaml.safe_load(path.read_text())
    record["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    path.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
    pending = list_pending()
    assert not any(r["id"] == rid for r in pending)


# ---------------------------------------------------------------------------
# Deterministic request_id idempotency
# ---------------------------------------------------------------------------

def test_same_action_vendor_amount_produces_same_id(approvals_dir):
    """Identical action/vendor/amount/date always yields the same request_id."""
    rid1 = create_request("purchase", "AWS", 312.0, {})
    rid2 = create_request("purchase", "AWS", 312.0, {})
    assert rid1 == rid2


def test_different_amounts_produce_different_ids(approvals_dir):
    """Different amounts must produce different request_ids."""
    rid1 = create_request("purchase", "AWS", 312.0, {})
    rid2 = create_request("purchase", "AWS", 313.0, {})
    assert rid1 != rid2
