"""Hash-chained tamper-evident audit log for the NemoClaw SMB-ops agent.

Each SMB action (payment, approval, vendor change, etc.) appends one JSONL line
whose hash = sha256(prev_hash + canonical_json(payload)), forming a chain where
any modification breaks every subsequent entry. Configurable via
NEMOCLAW_AUDIT_PATH; defaults to ~/.nemoclaw/audit.jsonl.

Public API:
  GENESIS_HASH      -- sentinel zero-hash for the chain head
  append_action()   -- write one chained SMB-ops entry, return the entry dict
  verify_chain()    -- walk from genesis, recompute every hash, return (ok, msg)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

GENESIS_HASH: str = "0" * 64

_VALID_ACTIONS = frozenset(
    {"payment", "approval_request", "approval_grant", "access_change", "vendor_switch"}
)

_DEFAULT_AUDIT_PATH = Path(
    os.environ.get("NEMOCLAW_AUDIT_PATH", os.path.expanduser("~/.nemoclaw/audit.jsonl"))
)


def _canonical(payload: dict) -> str:
    """Deterministic JSON for hashing: sorted keys, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_entry(prev_hash: str, payload: dict) -> str:
    """SHA-256 of (prev_hash concatenated with canonical payload)."""
    return hashlib.sha256((prev_hash + _canonical(payload)).encode("utf-8")).hexdigest()


def _resolve(path) -> Path:
    """Return the audit Path, falling back to the env-configured default."""
    return Path(path) if path is not None else _DEFAULT_AUDIT_PATH


def _read_head(audit_path: Path) -> tuple[str, int]:
    """Return (prev_hash, next_seq) from the tail of the audit file.

    Returns (GENESIS_HASH, 0) when the file does not yet exist or is empty.
    Raises RuntimeError on a corrupt tail to avoid silently re-anchoring on
    genesis, which would mask tampering.
    """
    if not audit_path.exists():
        return GENESIS_HASH, 0
    last_line = ""
    with audit_path.open("rb") as f:
        try:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return GENESIS_HASH, 0
            chunk = min(size, 4096)
            f.seek(-chunk, os.SEEK_END)
            tail = f.read().decode("utf-8", errors="replace")
        except OSError:
            return GENESIS_HASH, 0
    for line in reversed(tail.strip().splitlines()):
        if line.strip():
            last_line = line
            break
    if not last_line:
        return GENESIS_HASH, 0
    try:
        entry = json.loads(last_line)
        return entry["entry_hash"], int(entry["seq"]) + 1
    except (json.JSONDecodeError, KeyError, ValueError):
        raise RuntimeError(
            f"audit chain tail at {audit_path} is unreadable; refusing to append "
            f"(would mask tampering)"
        )


def append_action(
    action: str,
    vendor: str,
    amount: float,
    decision: str,
    actor: str,
    metadata: dict | None = None,
    path=None,
) -> dict:
    """Append one hash-chained SMB-ops entry and return the written entry dict.

    Validates `action` against the allowed enum at the trust boundary.
    Raises ValueError for unknown actions.
    """
    #COMPLETION_DRIVE: callers are internal; only action needs boundary validation
    if action not in _VALID_ACTIONS:
        raise ValueError(f"unknown action {action!r}; must be one of {sorted(_VALID_ACTIONS)}")

    audit_path = _resolve(path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    prev_hash, seq = _read_head(audit_path)

    payload: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": seq,
        "action": action,
        "vendor": vendor,
        "amount": amount,
        "decision": decision,
        "actor": actor,
        "metadata": metadata or {},
        "prev_hash": prev_hash,
    }
    payload["entry_hash"] = _hash_entry(prev_hash, payload)

    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return payload


def verify_chain(path=None) -> tuple[bool, str]:
    """Walk the audit file from genesis and recompute every hash.

    Returns (True, summary) when the chain is intact, or (False, error detail)
    on the first tamper/gap detected.
    """
    audit_path = _resolve(path)
    if not audit_path.exists():
        return True, "no audit file yet"

    prev = GENESIS_HASH
    expected_seq = 0

    with audit_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                return False, f"line {lineno}: malformed JSON ({exc})"
            if entry.get("prev_hash") != prev:
                return False, (
                    f"line {lineno}: prev_hash mismatch "
                    f"(expected {prev[:12]}, got {str(entry.get('prev_hash'))[:12]})"
                )
            if entry.get("seq") != expected_seq:
                return False, (
                    f"line {lineno}: seq mismatch "
                    f"(expected {expected_seq}, got {entry.get('seq')})"
                )
            stored = entry.get("entry_hash")
            payload_for_hash = {k: v for k, v in entry.items() if k != "entry_hash"}
            recomputed = _hash_entry(prev, payload_for_hash)
            if recomputed != stored:
                return False, (
                    f"line {lineno}: hash mismatch "
                    f"(stored {str(stored)[:12]}, recomputed {recomputed[:12]})"
                )
            prev = stored
            expected_seq += 1

    return True, f"chain ok ({expected_seq} entries)"
