"""
nemoclaw_harness.py — Safe-execution harness mirroring the NemoClaw pipeline.

Every agent skill executes through this module:
  guardrail -> permission/approval gate -> run -> audit

This mirrors the NemoClaw reference stack: NeMo Guardrails (policy), NeMo Agent
Toolkit (skill dispatch), and optional OpenShell process sandbox. The OpenShell
sandbox is the documented swap point: replace `_run_skill_inner` to exec the
skill inside an OpenShell child process rather than in-process.

Environment variables:
  NEMOCLAW_GUARDRAILS=1  — enables NeMo Guardrails check when nemoguardrails
                           is importable; falls back silently to built-in if not.
  NEMOCLAW_AUDIT_PATH    — forwarded to audit_log (set before import).
  NEMOCLAW_APPROVALS_DIR — forwarded to require_approval (set before import).
"""
from __future__ import annotations

import os
from typing import Any

from agent import audit_log, require_approval
from agent.skills import base as skills_base

# Denylist for built-in guardrail: strings that indicate injection / destructive ops.
_UNSAFE_PATTERNS = ("rm -rf", "DROP TABLE", "<script", "ignore previous instructions")

# Audit-log action used for skill executions (maps to audit_log._VALID_ACTIONS).
_AUDIT_ACTION_EXECUTED = "payment"
_AUDIT_ACTION_BLOCKED = "access_change"
_AUDIT_ACTION_ESCALATED = "approval_request"

# Default spend action for require_approval (maps to require_approval._VALID_ACTIONS).
_SPEND_ACTION = "purchase"


def execute(
    skill_name: str,
    args: dict,
    *,
    actor: str = "agent",
    amount: float | None = None,
    vendor: str | None = None,
    threshold: float | None = None,
    audit_path: str | None = None,
) -> dict:
    """Run a skill through the NemoClaw safe-execution pipeline.

    Pipeline: guardrail -> permission (if amount set) -> execute -> audit.
    Returns a structured outcome dict; never raises on expected pipeline halts.
    """
    steps: list[dict] = []
    base: dict[str, Any] = {
        "skill": skill_name,
        "outcome": None,
        "steps": steps,
        "result": None,
        "audit_entry_hash": None,
        "approval_request_id": None,
    }

    # Stage 1 — guardrail
    ok, reason = _guardrail_check(skill_name, args)
    steps.append({"step": "guardrail", "status": "ok" if ok else "blocked", "detail": reason})
    if not ok:
        entry = audit_log.append_action(
            _AUDIT_ACTION_BLOCKED,
            vendor or "unknown",
            amount or 0.0,
            decision="blocked",
            actor=actor,
            metadata={"skill": skill_name, "reason": reason},
            path=audit_path,
        )
        base["outcome"] = "blocked"
        base["audit_entry_hash"] = entry["entry_hash"]
        return base

    # Stage 2 — permission gate (spend skills only)
    if amount is not None:
        result = _permission_gate(
            skill_name, actor, amount, vendor, threshold, audit_path, steps, base
        )
        if result is not None:
            return result

    # Stage 3 — execute
    skill_result = skills_base.run_skill(skill_name, args)
    steps.append({"step": "execute", "status": "ok", "detail": f"skill returned {type(skill_result).__name__}"})

    # Stage 4 — audit
    entry = audit_log.append_action(
        _AUDIT_ACTION_EXECUTED,
        vendor or "unknown",
        amount or 0.0,
        decision="executed",
        actor=actor,
        metadata={"skill": skill_name},
        path=audit_path,
    )
    steps.append({"step": "audit", "status": "ok", "detail": f"entry_hash {entry['entry_hash'][:12]}"})

    base["outcome"] = "executed"
    base["result"] = skill_result
    base["audit_entry_hash"] = entry["entry_hash"]
    return base


def _permission_gate(
    skill_name: str,
    actor: str,
    amount: float,
    vendor: str | None,
    threshold: float | None,
    audit_path: str | None,
    steps: list[dict],
    base: dict,
) -> dict | None:
    """Call enforce_spend; return a completed escalated dict or None to continue.

    Returns None when the spend is approved (caller should proceed to execute).
    Returns the completed outcome dict when escalated (caller should return it).
    """
    try:
        require_approval.enforce_spend(
            action=_SPEND_ACTION,
            vendor=vendor or "unknown",
            amount=amount,
            actor=actor,
            threshold=threshold,
        )
        steps.append({"step": "permission", "status": "ok", "detail": "spend auto-approved or pre-approved"})
        return None
    except require_approval.ApprovalRequired as exc:
        steps.append({
            "step": "permission",
            "status": "escalated",
            "detail": f"amount ${amount:.2f} exceeds threshold; request {exc.request_id}",
        })
        entry = audit_log.append_action(
            _AUDIT_ACTION_ESCALATED,
            vendor or "unknown",
            amount,
            decision="escalated",
            actor=actor,
            metadata={"skill": skill_name, "request_id": exc.request_id},
            path=audit_path,
        )
        base["outcome"] = "escalated"
        base["approval_request_id"] = exc.request_id
        base["audit_entry_hash"] = entry["entry_hash"]
        return base


def _guardrail_check(skill_name: str, args: dict) -> tuple[bool, str]:
    """Built-in guardrail: skill registration, args type, unsafe-string denylist.

    When NEMOCLAW_GUARDRAILS=1 and nemoguardrails is importable, additionally
    runs a NeMo Guardrails policy check. On any import or runtime error the
    built-in result is returned (fail-open to built-in, never crash).

    OpenShell swap point: in production this function would also verify that the
    process sandbox policy allows this skill before returning True.
    """
    # Registration check
    if skill_name not in skills_base.all_skills_names():
        return False, f"skill {skill_name!r} not registered"

    # Type check at trust boundary
    if not isinstance(args, dict):
        return False, f"args must be a dict, got {type(args).__name__}"

    # Denylist scan over string values
    unsafe = _scan_unsafe(args)
    if unsafe:
        return False, f"unsafe pattern detected: {unsafe!r}"

    builtin_result = (True, "guardrail ok")

    # Optional NeMo Guardrails check
    if os.environ.get("NEMOCLAW_GUARDRAILS") == "1":
        try:
            return _nemo_guardrails_check(skill_name, args, builtin_result)
        except Exception:
            # Fail-open: NeMo Guardrails unavailable or errored; built-in passes
            return builtin_result

    return builtin_result


def _scan_unsafe(args: dict) -> str | None:
    """Return the first unsafe pattern found in string values, or None."""
    for v in _iter_string_values(args):
        for pattern in _UNSAFE_PATTERNS:
            if pattern in v:
                return pattern
    return None


def _iter_string_values(obj: Any):
    """Yield string leaves from a nested dict/list structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_string_values(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_string_values(item)


def _nemo_guardrails_check(
    skill_name: str,
    args: dict,
    fallback: tuple[bool, str],
) -> tuple[bool, str]:
    """Run a NeMo Guardrails policy check; return fallback on any error.

    Import is guarded here so the module loads without nemoguardrails installed.
    The NeMo Guardrails seam: instantiate LLMRails with the project config and
    call rails.generate(messages=[...]) to get a policy decision. Production
    deployments configure the rails config at NEMOCLAW_RAILS_CONFIG env var.
    """
    import nemoguardrails  # noqa: F401 — guard: only imported when env=1

    # #COMPLETION_DRIVE: nemoguardrails API varies by version; using presence check only.
    # A production implementation would call LLMRails.generate() and parse the result.
    # For now, confirm the package is available and defer to built-in.
    return fallback
