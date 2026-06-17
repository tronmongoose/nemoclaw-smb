"""
approval_gate_skill.py — Thin passthrough over require_approval.list_pending and .decide.

Exports: skill (registered on import)
"""

from __future__ import annotations

from agent import require_approval

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list_pending", "decide"],
            "description": "list_pending returns all pending requests; decide approves/denies one.",
        },
        "request_id": {
            "type": "string",
            "description": "Required for action=decide.",
        },
        "approved": {
            "type": "boolean",
            "description": "Required for action=decide.",
        },
        "decided_by": {
            "type": "string",
            "description": "Human identifier for the decision (default: human).",
            "default": "human",
        },
    },
    "required": ["action"],
}


def _run(args: dict) -> dict:
    """Route list_pending or decide; validate required fields for decide."""
    action: str = args["action"]

    if action == "list_pending":
        pending = require_approval.list_pending()
        return {"pending": pending, "count": len(pending)}

    if action == "decide":
        request_id: str = args["request_id"]
        approved: bool = bool(args["approved"])
        decided_by: str = args.get("decided_by") or "human"
        record = require_approval.decide(request_id, approved, decided_by)
        return {"record": record}

    return {"error": f"unknown action: {action!r}"}


skill = register(Skill(
    name="approval_gate_skill",
    description="List pending spend approvals or record a human approve/deny decision.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
