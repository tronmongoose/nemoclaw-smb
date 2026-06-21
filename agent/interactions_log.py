"""Hash-chained log of sponsor-technology interactions (Hermes/Nous, Nemotron/NVIDIA, Stripe).

Parallel to agent/audit_log.py but telemetry-focused: every model call and payment
interaction appends one JSONL line whose hash chains to the previous, so the feed of
live and historical interactions is tamper-evident. Configurable via
NEMOCLAW_INTERACTIONS_PATH; demo default audit/demo_interactions.jsonl (cwd-relative).

Public API:
  GENESIS_HASH          -- sentinel zero-hash for the chain head
  append_interaction()  -- write one chained interaction entry, return the entry dict
  read_interactions()   -- read recent entries (newest last), optional sponsor/segment filter
  verify_chain()        -- walk from genesis, recompute every hash, return (ok, msg)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

GENESIS_HASH: str = "0" * 64

_SPONSORS = frozenset({"Nous Research", "NVIDIA", "Stripe", "ConductorOne"})

_DEFAULT_PATH = Path(
    os.environ.get("NEMOCLAW_INTERACTIONS_PATH", "audit/demo_interactions.jsonl")
)


def _canonical(payload: dict) -> str:
    """Deterministic JSON for hashing: sorted keys, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_entry(prev_hash: str, payload: dict) -> str:
    """SHA-256 of (prev_hash concatenated with canonical payload)."""
    return hashlib.sha256((prev_hash + _canonical(payload)).encode("utf-8")).hexdigest()


def _resolve(path) -> Path:
    """Return the interactions Path, falling back to the env-configured default."""
    return Path(path) if path is not None else _DEFAULT_PATH


def _read_head(p: Path) -> tuple[str, int]:
    """Return (prev_hash, next_seq) from the tail; (GENESIS, 0) when absent/empty."""
    if not p.exists():
        return GENESIS_HASH, 0
    with p.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if size == 0:
            return GENESIS_HASH, 0
        f.seek(-min(size, 4096), os.SEEK_END)
        tail = f.read().decode("utf-8", errors="replace")
    for line in reversed(tail.strip().splitlines()):
        if line.strip():
            try:
                entry = json.loads(line)
                return entry["entry_hash"], int(entry["seq"]) + 1
            except (json.JSONDecodeError, KeyError, ValueError):
                raise RuntimeError(
                    f"interactions chain tail at {p} is unreadable; refusing to append"
                )
    return GENESIS_HASH, 0


def append_interaction(
    sponsor: str,
    op: str,
    segment: str = "",
    status: str = "ok",
    model: Optional[str] = None,
    latency_ms: Optional[float] = None,
    mode: Optional[str] = None,
    metadata: Optional[dict] = None,
    path=None,
) -> dict:
    """Append one hash-chained interaction entry and return it.

    sponsor must be one of the four sponsor technologies. Never raises on a write
    fault beyond the boundary check; callers treat logging as best-effort telemetry.
    """
    if sponsor not in _SPONSORS:
        raise ValueError(f"unknown sponsor {sponsor!r}; must be one of {sorted(_SPONSORS)}")

    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    prev_hash, seq = _read_head(p)

    payload: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": seq,
        "sponsor": sponsor,
        "op": op,
        "segment": segment,
        "status": status,
        "model": model,
        "latency_ms": latency_ms,
        "mode": mode,
        "metadata": metadata or {},
        "prev_hash": prev_hash,
    }
    payload["entry_hash"] = _hash_entry(prev_hash, payload)

    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return payload


def read_interactions(
    limit: int = 100,
    sponsor: Optional[str] = None,
    segment: Optional[str] = None,
    path=None,
) -> list[dict]:
    """Return up to `limit` most-recent entries (newest last), optionally filtered."""
    p = _resolve(path)
    if not p.exists():
        return []
    out: list[dict] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if sponsor and entry.get("sponsor") != sponsor:
                continue
            if segment and entry.get("segment") != segment:
                continue
            out.append(entry)
    return out[-limit:]


def verify_chain(path=None) -> tuple[bool, str]:
    """Walk from genesis and recompute every hash; (ok, summary) or first fault."""
    p = _resolve(path)
    if not p.exists():
        return True, "no interactions file yet"
    prev = GENESIS_HASH
    expected_seq = 0
    with p.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                return False, f"line {lineno}: malformed JSON ({exc})"
            if entry.get("prev_hash") != prev:
                return False, f"line {lineno}: prev_hash mismatch"
            if entry.get("seq") != expected_seq:
                return False, f"line {lineno}: seq mismatch"
            stored = entry.get("entry_hash")
            recomputed = _hash_entry(prev, {k: v for k, v in entry.items() if k != "entry_hash"})
            if recomputed != stored:
                return False, f"line {lineno}: hash mismatch"
            prev = stored
            expected_seq += 1
    return True, f"chain ok ({expected_seq} entries)"
