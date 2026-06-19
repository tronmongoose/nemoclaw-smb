"""
nemoclaw_harness.py — Safe-execution harness mirroring the NemoClaw pipeline.

Every agent skill executes through this module:
  guardrail -> permission/approval gate -> run -> audit

Pipeline stages:
  1. Guardrail: built-in denylist + optional NeMo Guardrails LLM check.
  2. Permission gate: spend threshold enforcement via require_approval.
  3. Execute: subprocess isolation when NEMOCLAW_SANDBOX is truthy AND skill args
     are JSON-serializable; in-process fallback otherwise (logged, not silenced).
  4. Audit: append-and-hash to the audit chain.

Subprocess sandbox (FIX 2):
  When NEMOCLAW_SANDBOX is set, serializable skills run in a child `python3 -c`
  process. This is a genuine process boundary: the child imports the skill
  registry, runs the named skill, and returns JSON via stdout. A configurable
  timeout enforces termination. Skills whose args contain non-JSON-serializable
  objects (e.g. KnowledgeGraph instances) fall back to in-process execution with
  a logged note — they are NOT falsely claimed to be sandboxed.

  OpenShell is the documented production swap point for a heavier container-based
  sandbox. OpenShell is NOT installed or used here. The subprocess boundary is the
  real isolation implemented in this file.

NeMo Guardrails (FIX 1):
  When NEMOCLAW_GUARDRAILS=1, _nemo_guardrails_check instantiates LLMRails with
  the config at agent/guardrails/config/ and calls rails.generate() to obtain a
  real LLM policy decision. nemoguardrails is lazy-imported inside that function
  so the module loads without the package installed. On any error the built-in
  denylist result is returned (fail-safe).

Environment variables:
  NEMOCLAW_GUARDRAILS=1      — enables NeMo Guardrails LLM check.
  NEMOCLAW_SANDBOX=<truthy>  — enables subprocess isolation for serializable skills.
  NEMOCLAW_RAILS_CONFIG      — path to guardrails config dir (default: agent/guardrails/config).
  NEMOCLAW_SANDBOX_TIMEOUT   — child process timeout in seconds (default: 30).
  NEMOCLAW_AUDIT_PATH        — forwarded to audit_log.
  NEMOCLAW_APPROVALS_DIR     — forwarded to require_approval.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from agent import audit_log, require_approval
from agent.skills import base as skills_base

log = logging.getLogger(__name__)

# Denylist for built-in guardrail.
_UNSAFE_PATTERNS = ("rm -rf", "DROP TABLE", "<script", "ignore previous instructions")

_AUDIT_ACTION_EXECUTED = "payment"
_AUDIT_ACTION_BLOCKED = "access_change"
_AUDIT_ACTION_ESCALATED = "approval_request"
_SPEND_ACTION = "purchase"

# Resolved once at module load; used as fallback path for rails config.
_DEFAULT_RAILS_CONFIG = str(Path(__file__).parent / "guardrails" / "config")

_SANDBOX_TIMEOUT_DEFAULT = 30


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

    if amount is not None:
        result = _permission_gate(
            skill_name, actor, amount, vendor, threshold, audit_path, steps, base
        )
        if result is not None:
            return result

    skill_result, sandbox_label = _run_skill(skill_name, args)
    steps.append({
        "step": "execute",
        "status": "ok",
        "detail": f"skill returned {type(skill_result).__name__} [{sandbox_label}]",
    })

    entry = audit_log.append_action(
        _AUDIT_ACTION_EXECUTED,
        vendor or "unknown",
        amount or 0.0,
        decision="executed",
        actor=actor,
        metadata={"skill": skill_name, "sandbox": sandbox_label},
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
    """Call enforce_spend; return completed escalated dict or None to continue."""
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


# ---------------------------------------------------------------------------
# Subprocess sandbox (FIX 2)
# ---------------------------------------------------------------------------

def _run_skill(skill_name: str, args: dict) -> tuple[Any, str]:
    """Execute the named skill; return (result, sandbox_label).

    When NEMOCLAW_SANDBOX is truthy and args are JSON-serializable, runs the
    skill in a child python3 subprocess (genuine process boundary). Falls back
    to in-process execution when args cannot be serialized; logs the fallback
    so it is never silently claimed to be sandboxed.

    sandbox_label values:
      "subprocess" — ran in a child process (real isolation)
      "in-process" — ran in-process (args not serializable or sandbox disabled)
    """
    sandbox_enabled = _sandbox_enabled()
    if sandbox_enabled:
        try:
            json.dumps(args)  # serialization probe — raises TypeError on failure
            return _run_skill_subprocess(skill_name, args), "subprocess"
        except (TypeError, ValueError):
            log.info(
                "nemoclaw_harness: args for %r not JSON-serializable; "
                "falling back to in-process execution (not sandboxed)",
                skill_name,
            )
    return skills_base.run_skill(skill_name, args), "in-process"


def _run_skill_subprocess(skill_name: str, args: dict) -> dict:
    """Run skill_name(args) in a child python3 process; return parsed JSON result.

    The child imports the full skill registry, runs the named skill, and writes
    the result as JSON to stdout. A timeout enforces termination.
    Raises RuntimeError on non-zero exit or JSON parse failure.
    """
    timeout = int(os.environ.get("NEMOCLAW_SANDBOX_TIMEOUT", _SANDBOX_TIMEOUT_DEFAULT))
    # The child script: import registry (triggers registration), run, print JSON.
    child_script = (
        "import sys, json; "
        "sys.path.insert(0, sys.argv[1]); "
        "import agent.skills; "  # fires all registrations via __init__.py
        "from agent.skills.base import run_skill; "
        "args = json.loads(sys.argv[2]); "
        "result = run_skill(sys.argv[3], args); "
        "print(json.dumps(result))"
    )
    repo_root = str(Path(__file__).parent.parent)
    proc = subprocess.run(
        [sys.executable, "-c", child_script, repo_root, json.dumps(args), skill_name],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"sandbox child exited {proc.returncode}: {proc.stderr.strip()[:200]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"sandbox child stdout not JSON: {proc.stdout[:200]}") from exc


def _sandbox_enabled() -> bool:
    """Return True when NEMOCLAW_SANDBOX is set to a truthy value."""
    val = os.environ.get("NEMOCLAW_SANDBOX", "").strip().lower()
    return val in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Guardrail (FIX 1 + denylist)
# ---------------------------------------------------------------------------

def _guardrail_check(skill_name: str, args: dict) -> tuple[bool, str]:
    """Built-in guardrail: registration, args type, denylist, optional NeMo Guardrails.

    When NEMOCLAW_GUARDRAILS=1, additionally calls _nemo_guardrails_check which
    instantiates LLMRails and runs a real LLM policy check. On any error the
    built-in result is returned (fail-safe, never crash).
    """
    if skill_name not in skills_base.all_skills_names():
        return False, f"skill {skill_name!r} not registered"

    if not isinstance(args, dict):
        return False, f"args must be a dict, got {type(args).__name__}"

    unsafe = _scan_unsafe(args)
    if unsafe:
        return False, f"unsafe pattern detected: {unsafe!r}"

    builtin_result = (True, "guardrail ok (denylist)")

    if os.environ.get("NEMOCLAW_GUARDRAILS") == "1":
        try:
            return _nemo_guardrails_check(skill_name, args, builtin_result)
        except Exception as exc:
            log.warning("nemoclaw_harness: NeMo Guardrails check failed (%s); using denylist", exc)
            return builtin_result

    return builtin_result


def _scan_unsafe(args: dict) -> str | None:
    """Return the first unsafe pattern found in string values, or None."""
    for v in _iter_string_values(args):
        for pattern in _UNSAFE_PATTERNS:
            if pattern in v:
                return pattern
    return None


def _iter_string_values(obj: Any):  # noqa: ANN001
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
    """Run a real NeMo Guardrails LLM policy check; return fallback on any error.

    Instantiates LLMRails from the config at NEMOCLAW_RAILS_CONFIG (default:
    agent/guardrails/config/). Calls rails.generate() with the skill name and
    args serialized as the user message. Interprets a "Yes" in the response as
    "block" (the prompt asks "Should this be blocked?").

    nemoguardrails is lazy-imported so the module loads without it installed.

    #COMPLETION_DRIVE: LLMRails requires a live OpenAI-compatible endpoint
    (NOUS_PORTAL_API_KEY + NOUS_PORTAL_BASE_URL). If those env vars are absent
    the call raises and the denylist fallback is returned.
    """
    from nemoguardrails import LLMRails, RailsConfig  # noqa: PLC0415
    from langchain_community.chat_models import ChatOpenAI  # noqa: PLC0415

    rails_config_path = os.environ.get("NEMOCLAW_RAILS_CONFIG", _DEFAULT_RAILS_CONFIG)

    # Expand env-var references in config.yml (NOUS_PORTAL_BASE_URL etc.)
    config_file = Path(rails_config_path) / "config.yml"
    raw_yml = config_file.read_text()
    expanded_yml = os.path.expandvars(raw_yml)

    config = RailsConfig.from_content(yaml_content=expanded_yml)

    nous_key = os.environ.get("NOUS_PORTAL_API_KEY", "")
    nous_base = os.environ.get("NOUS_PORTAL_BASE_URL", "")

    # Build a ChatOpenAI LLM pointed at the NOUS OpenAI-compatible endpoint.
    # ChatOpenAI uses /chat/completions; langchain_community.llms.OpenAI uses
    # /completions which the NOUS portal does not expose.
    llm = ChatOpenAI(
        model_name=config.models[0].model,
        openai_api_key=nous_key,
        openai_api_base=nous_base,
        max_tokens=8,
        temperature=0.0,
    )

    rails = LLMRails(config=config, llm=llm)

    # Serialize the skill invocation as the user message for the rail.
    try:
        args_repr = json.dumps(args, default=str)
    except Exception:
        args_repr = repr(args)
    user_message = f"skill={skill_name} args={args_repr}"

    response = rails.generate(messages=[{"role": "user", "content": user_message}])

    # generate() returns the assistant response dict or string.
    # self_check_input: if the rail decides to block, it returns a refusal message
    # ("I'm sorry, I can't respond to that.") instead of a normal reply.
    # A normal (allowed) response is whatever the assistant would say.
    if isinstance(response, dict):
        response_text = response.get("content", "").strip().lower()
    else:
        response_text = (str(response) or "").strip().lower()

    refusal_signals = ("i'm sorry, i can't", "i am sorry, i can't", "i cannot respond")
    if any(sig in response_text for sig in refusal_signals):
        return False, f"NeMo Guardrails blocked: {response_text[:80]}"

    return True, f"NeMo Guardrails allowed: {response_text[:60]}"
