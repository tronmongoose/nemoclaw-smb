"""tests/test_issuing.py -- Tests for payments/issuing.py (Stripe Issuing for Agents).

Asserts:
- Card issued with $75 (7500c) cap
- MCC restrictions include 7349 and 5251
- Expiry is same-day EOD (23:59:59)
- Raw PAN never appears in any return value, log, or audit entry
- Revoke logs the reason

All tests run in DEMO_MODE with no credentials.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("DEMO_MODE", "true")

import agent.audit_log as _audit_log_mod  # noqa: E402 -- must follow env setup

# PAN pattern: 16 consecutive digits not bounded by word chars, not the genesis hash
_PAN_RE = re.compile(r"(?<!\w)\d{16}(?!\w)")

_GENESIS_ZEROS = "0" * 64


def _no_pan(text: str) -> bool:
    """Return True when text contains no 16-digit PAN-like string."""
    matches = _PAN_RE.findall(text)
    # genesis hash zeros are 64 chars, not 16-digit PANs -- exclude them
    return all(m == _GENESIS_ZEROS[:16] for m in matches) if matches else True


def _read_audit_tail(audit_path: str, n: int = 5) -> list[dict]:
    """Read the last n entries from a JSONL audit file."""
    with open(audit_path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return [json.loads(l) for l in lines[-n:]]


def _with_audit(tmp_path):
    """Return a context: patches _DEFAULT_AUDIT_PATH and returns the path str."""
    return str(tmp_path / "audit.jsonl")


def _patch_audit(tmp_path):
    """Redirect audit_log to write into tmp_path for this test."""
    _audit_log_mod._DEFAULT_AUDIT_PATH = Path(tmp_path / "audit.jsonl")


def test_card_issued_with_correct_cap(tmp_path):
    """issue_cleaner_card returns CleanerCardResult with 7500c cap."""
    _patch_audit(tmp_path)
    from payments.issuing import issue_cleaner_card

    result = issue_cleaner_card(
        job_id="job-test-001",
        property_id="prop-001",
        cleaner_id="crew-001",
    )
    assert result.amount_cap_cents == 7500


def test_card_mcc_restrictions(tmp_path):
    """issue_cleaner_card enforces MCC 7349 (cleaning) and 5251 (hardware)."""
    _patch_audit(tmp_path)
    from payments.issuing import issue_cleaner_card

    result = issue_cleaner_card(
        job_id="job-test-002",
        property_id="prop-002",
        cleaner_id="crew-002",
    )
    assert "7349" in result.mcc_list
    assert "5251" in result.mcc_list


def test_card_expiry_same_day_eod(tmp_path):
    """issue_cleaner_card expiry is same-day 23:59:59 UTC."""
    _patch_audit(tmp_path)
    from datetime import datetime, timezone

    from payments.issuing import issue_cleaner_card

    result = issue_cleaner_card(
        job_id="job-test-003",
        property_id="prop-003",
        cleaner_id="crew-001",
    )
    expiry = datetime.fromisoformat(result.expiry_utc)
    assert expiry.hour == 23
    assert expiry.minute == 59
    assert expiry.second == 59
    today = datetime.now(timezone.utc).date()
    assert expiry.date() == today


def test_no_pan_in_result(tmp_path):
    """Raw PAN never appears in the CleanerCardResult fields."""
    _patch_audit(tmp_path)
    from payments.issuing import issue_cleaner_card

    result = issue_cleaner_card(
        job_id="job-test-004",
        property_id="prop-004",
        cleaner_id="crew-002",
    )
    result_text = json.dumps(result.__dict__)
    assert _no_pan(result_text), f"PAN-like 16-digit string found in result: {result_text}"


def test_no_pan_in_audit_entries(tmp_path):
    """Raw PAN never appears in audit log entries written by issue_cleaner_card."""
    _patch_audit(tmp_path)
    audit_path = str(_audit_log_mod._DEFAULT_AUDIT_PATH)
    from payments.issuing import issue_cleaner_card

    issue_cleaner_card(
        job_id="job-test-005",
        property_id="prop-005",
        cleaner_id="crew-001",
    )
    entries = _read_audit_tail(audit_path, n=10)
    for entry in entries:
        text = json.dumps(entry)
        assert _no_pan(text), f"PAN-like string in audit entry: {text}"


def test_card_token_not_pan(tmp_path):
    """card_token is a prefixed opaque token, not a 16-digit PAN."""
    _patch_audit(tmp_path)
    from payments.issuing import issue_cleaner_card

    result = issue_cleaner_card(
        job_id="job-test-006",
        property_id="prop-001",
        cleaner_id="crew-002",
    )
    assert result.card_token.startswith("tok_")
    assert not _PAN_RE.match(result.card_token)


def test_revoke_logs_reason(tmp_path):
    """revoke_card returns RevokeResult and logs the reason in the audit."""
    _patch_audit(tmp_path)
    audit_path = str(_audit_log_mod._DEFAULT_AUDIT_PATH)
    from payments.issuing import revoke_card

    reason = "job-completed-early"
    result = revoke_card(card_id="ic_abc123", reason=reason)

    assert result.status == "canceled"
    assert result.reason == reason

    entries = _read_audit_tail(audit_path, n=5)
    reasons_logged = [
        e["metadata"].get("reason")
        for e in entries
        if e.get("decision") == "card_revoked"
    ]
    assert reason in reasons_logged


def test_custom_amount_cents(tmp_path):
    """issue_cleaner_card accepts a custom amount_cents override."""
    _patch_audit(tmp_path)
    from payments.issuing import issue_cleaner_card

    result = issue_cleaner_card(
        job_id="job-test-007",
        property_id="prop-001",
        cleaner_id="crew-001",
        amount_cents=5000,
    )
    assert result.amount_cap_cents == 5000
