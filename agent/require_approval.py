"""
Spend approval gate for nemoclaw-smb agent actions.

Exports:
  requires_approval(action, amount, threshold) -> bool
  ApprovalRequired — raised by enforce_spend when approval is needed
  create_request(action, vendor, amount, context, ttl_seconds) -> str
  decide(request_id, approved, decided_by) -> dict
  check(request_id) -> dict
  is_approved(request_id) -> bool
  list_pending() -> list[dict]
  enforce_spend(action, vendor, amount, actor, context) -> dict
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

_VALID_ACTIONS = {"purchase", "subscribe", "renew", "refund", "transfer", "contract"}

_APPROVALS_DIR = Path(
    os.environ.get("NEMOCLAW_APPROVALS_DIR", os.path.expanduser("~/.nemoclaw/approvals"))
)


def _approvals_dir() -> Path:
    """Return and ensure the approvals directory exists."""
    d = Path(os.environ.get("NEMOCLAW_APPROVALS_DIR", str(_APPROVALS_DIR)))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _request_path(request_id: str) -> Path:
    """Return YAML file path for a given request_id."""
    return _approvals_dir() / f"{request_id}.yaml"


def _default_threshold() -> float:
    """Read threshold from env, default 100."""
    return float(os.getenv("SPEND_APPROVAL_THRESHOLD", "100"))


def _request_id(action: str, vendor: str, amount: float) -> str:
    """Deterministic 12-char sha256 id keyed on action:vendor:amount:date."""
    date = datetime.now().strftime("%Y%m%d")
    raw = f"{action}:{vendor}:{amount}:{date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def requires_approval(
    action: str, amount: float, threshold: float | None = None
) -> bool:
    """Return True when amount exceeds threshold."""
    limit = threshold if threshold is not None else _default_threshold()
    return amount > limit


class ApprovalRequired(Exception):
    """Raised by enforce_spend when a spend action needs human approval."""

    def __init__(self, request_id: str, action: str, vendor: str, amount: float) -> None:
        """Store request_id and context for the caller."""
        self.request_id = request_id
        self.action = action
        self.vendor = vendor
        self.amount = amount
        super().__init__(
            f"Spend approval required: {request_id} — {action}/{vendor} ${amount:.2f}"
        )


def _validate_inputs(action: str, amount: float) -> None:
    """Validate action is in enum and amount is non-negative."""
    if action not in _VALID_ACTIONS:
        raise ValueError(f"action must be one of {sorted(_VALID_ACTIONS)}, got {action!r}")
    if amount < 0:
        raise ValueError(f"amount must be >= 0, got {amount}")


def create_request(
    action: str,
    vendor: str,
    amount: float,
    context: dict[str, Any],
    ttl_seconds: int = 86400,
) -> str:
    """Create a pending approval record. Returns deterministic request_id."""
    _validate_inputs(action, amount)
    request_id = _request_id(action, vendor, amount)
    path = _request_path(request_id)

    if path.exists():
        existing = yaml.safe_load(path.read_text())
        if existing.get("status") == "pending":
            return request_id

    now = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "id": request_id,
        "action": action,
        "vendor": vendor,
        "amount": amount,
        "context": context,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "status": "pending",
    }
    path.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
    return request_id


def decide(request_id: str, approved: bool, decided_by: str) -> dict:
    """Record a human decision on a pending request. Returns the updated record."""
    path = _request_path(request_id)
    if not path.exists():
        raise KeyError(f"No approval request found: {request_id}")

    record = yaml.safe_load(path.read_text())
    if record.get("status") != "pending":
        return record

    expires_at = datetime.fromisoformat(record["expires_at"])
    now = datetime.now(timezone.utc)
    if now > expires_at:
        record["status"] = "expired"
        path.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
        return record

    record["status"] = "approved" if approved else "denied"
    record["decided_at"] = now.isoformat()
    record["decided_by"] = decided_by
    path.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
    return record


def check(request_id: str) -> dict:
    """Return the current record, auto-expiring stale pending requests."""
    path = _request_path(request_id)
    if not path.exists():
        raise KeyError(f"No approval request found: {request_id}")

    record = yaml.safe_load(path.read_text())
    if record.get("status") == "pending":
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            record["status"] = "expired"
            path.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
    return record


def is_approved(request_id: str) -> bool:
    """Return True only when the request exists and status is approved."""
    try:
        return check(request_id).get("status") == "approved"
    except KeyError:
        return False


def list_pending() -> list[dict]:
    """Return all pending (non-expired) approval records, sorted by created_at."""
    pending = []
    for path in sorted(_approvals_dir().glob("*.yaml")):
        try:
            record = yaml.safe_load(path.read_text())
        except Exception:
            continue
        if record.get("status") == "pending":
            expires_at = datetime.fromisoformat(record["expires_at"])
            if datetime.now(timezone.utc) <= expires_at:
                pending.append(record)
    return pending


def _find_existing_request(action: str, vendor: str, amount: float) -> str | None:
    """Return request_id of an existing record for this spend key, or None."""
    #COMPLETION_DRIVE: deterministic id means we can derive without scanning
    rid = _request_id(action, vendor, amount)
    if _request_path(rid).exists():
        return rid
    return None


def enforce_spend(
    action: str,
    vendor: str,
    amount: float,
    actor: str = "agent",
    context: dict[str, Any] | None = None,
) -> dict:
    """
    Gate spend by threshold. Raises ApprovalRequired when needed and not yet granted.

    Returns the approval record (or a synthetic auto-approved record for under-threshold).
    """
    _validate_inputs(action, amount)
    ctx = context or {}

    if not requires_approval(action, amount):
        return {
            "id": None,
            "action": action,
            "vendor": vendor,
            "amount": amount,
            "status": "auto-approved",
            "actor": actor,
        }

    rid = _find_existing_request(action, vendor, amount)
    if rid and is_approved(rid):
        return check(rid)

    request_id = create_request(action, vendor, amount, ctx)
    raise ApprovalRequired(request_id, action, vendor, amount)
