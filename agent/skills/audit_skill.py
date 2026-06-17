"""
audit_skill.py — Verify the hash-chained audit log and return recent entries.

Exports: skill (registered on import)
"""

from __future__ import annotations

import json
from pathlib import Path

from agent import audit_log

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["verify_chain", "recent"],
            "description": "verify_chain checks integrity; recent returns last N entries.",
        },
        "last_n": {
            "type": "integer",
            "description": "Number of entries to return for action=recent (default 10).",
            "default": 10,
        },
        "audit_path": {
            "type": "string",
            "description": "Override path for the audit JSONL file.",
        },
    },
    "required": ["action"],
}

#COMPLETION_DRIVE: audit_path defaults to None; audit_log module resolves to env default


def _recent_entries(path_str: str | None, last_n: int) -> list[dict]:
    """Return last_n lines from the audit file; returns [] when file absent."""
    from agent.audit_log import _DEFAULT_AUDIT_PATH, _resolve  # noqa: PLC0415
    audit_path = _resolve(path_str)
    if not audit_path.exists():
        return []
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    tail = lines[-last_n:] if len(lines) >= last_n else lines
    entries = []
    for line in tail:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _run(args: dict) -> dict:
    """Verify chain integrity or return recent entries from the audit log."""
    action: str = args["action"]
    audit_path: str | None = args.get("audit_path")

    if action == "verify_chain":
        ok, msg = audit_log.verify_chain(path=audit_path)
        return {"ok": ok, "message": msg}

    if action == "recent":
        last_n = int(args.get("last_n") or 10)
        entries = _recent_entries(audit_path, last_n)
        return {"entries": entries, "count": len(entries)}

    return {"error": f"unknown action: {action!r}"}


skill = register(Skill(
    name="audit_skill",
    description="Verify audit chain integrity or retrieve recent hash-chained audit log entries.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
