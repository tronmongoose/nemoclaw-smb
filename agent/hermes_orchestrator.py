"""
hermes_orchestrator.py — Bounded Hermes agent loop driving skills through the NemoClaw harness.

Exports:
    orchestrate  — run the bounded multi-step CFO orchestration loop
    _build_system_prompt — construct the system prompt with skill manifest
    _parse_action        — extract the first JSON action dict from model output
    _run_step            — dispatch one run_skill action through the harness
"""

from __future__ import annotations

import json
import re
from typing import Callable

import agent.skills.anomaly_detect_skill  # noqa: F401 — registers anomaly_detect_skill
import agent.skills.invoice_ingest_skill   # noqa: F401 — registers invoice_ingest_skill
import agent.skills.vendor_analyze_skill   # noqa: F401 — registers vendor_analyze_skill
import agent.skills.handle_402_skill       # noqa: F401 — registers handle_402_skill
import agent.skills.access_governance_skill  # noqa: F401 — registers access_governance_skill
import agent.skills.onboarding_skill       # noqa: F401 — registers onboarding_skill
import agent.skills.approval_gate_skill    # noqa: F401 — registers approval_gate_skill
import agent.skills.audit_skill            # noqa: F401 — registers audit_skill

from agent.hermes_client import call_hermes
from agent.nemoclaw_harness import execute
from agent.skills.base import all_skills, to_nat_function

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _build_system_prompt(
    intent: str,
    context: dict | None,
    graph,
    threshold: float | None,
    executed_history: list[dict] | None = None,
) -> str:
    """Build the CFO orchestrator system prompt with the skill manifest.

    Includes the skill manifest, optional graph/context summary, the exact JSON
    action protocol, and the history of already-executed skills for this run.
    """
    manifest = json.dumps([to_nat_function(s) for s in all_skills()], indent=2)

    ctx_block = ""
    if context:
        ctx_block = f"\nContext provided by caller:\n{json.dumps(context, indent=2)}\n"
    if graph is not None:
        try:
            vendors = [n["label"] for n in graph.nodes() if n.get("type") == "vendor"]
            ctx_block += f"\nKnowledge graph vendors: {vendors}\n"
        except Exception:  # noqa: BLE001
            pass

    threshold_note = f"\nSpend threshold: ${threshold:.2f} — amounts above this escalate." if threshold else ""

    history_block = ""
    if executed_history:
        lines = [
            f"  - {h['skill']} (args={json.dumps(h['args'])}) → outcome={h['outcome']}"
            for h in executed_history
        ]
        history_block = (
            "\nSkills already executed this run (DO NOT repeat unless new information demands it):\n"
            + "\n".join(lines)
            + "\n"
        )

    finalize_instruction = (
        "\nCRITICAL RULES:\n"
        "1. Do NOT call a skill that has already been executed unless new information requires it.\n"
        "2. When the user's intent has been satisfied by the observations so far, you MUST respond "
        'with {"action":"final","summary":"<concise summary of findings and decision>"}.\n'
        "3. Prefer finalizing over repeating work. If you have run one or more skills and have "
        "enough information to answer the intent, finalize NOW.\n"
    )

    return (
        f"You are the SMB CFO orchestrator powered by Hermes. Your job is to fulfill the "
        f"following intent by dispatching skills through the NemoClaw safe-execution harness.\n\n"
        f"Intent: {intent}\n"
        f"{ctx_block}"
        f"{threshold_note}\n\n"
        f"Available skills (NeMo Agent Toolkit manifest):\n{manifest}\n\n"
        f"{history_block}"
        f"{finalize_instruction}\n"
        f"Reply with EXACTLY ONE JSON object per turn — no prose before or after:\n"
        f'  run_skill: {{"action":"run_skill","skill":<name>,"args":{{...}},"reason":"..."}}\n'
        f'  done:      {{"action":"final","summary":"..."}}\n'
        f'  escalate:  {{"action":"escalate","reason":"..."}}\n'
        f"When the goal is achieved, reply with the final action."
    )


def _parse_action(text: str) -> dict | None:
    """Extract the first JSON object from the model reply; return None on failure.

    Tolerates surrounding prose and partial mock prefixes.
    """
    stripped = re.sub(r"^\[hermes-mock\]\s*", "", text.strip())
    m = _JSON_RE.search(stripped)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _run_step(
    action: dict,
    step_idx: int,
    threshold: float | None,
    audit_path: str | None,
    seed_invoices_fn,
) -> dict:
    """Dispatch one run_skill action through the harness; return a step record.

    Injects seed invoices when the skill args contain the '__SEED__' sentinel
    (used by the scripted mock to reference real data without circular imports).
    """
    skill_name: str = action.get("skill", "")
    args: dict = action.get("args", {})

    args = {
        k: (seed_invoices_fn() if v == "__SEED__" else v)
        for k, v in args.items()
    }

    amount: float | None = args.get("amount") if isinstance(args.get("amount"), (int, float)) else None
    vendor: str | None = args.get("vendor")

    result = execute(
        skill_name,
        args,
        actor="hermes",
        amount=amount,
        vendor=vendor,
        threshold=threshold,
        audit_path=audit_path,
    )

    return {
        "step": step_idx,
        "action": "run_skill",
        "skill": skill_name,
        "args": args,
        "reason": action.get("reason", ""),
        "outcome": result.get("outcome"),
        "audit_entry_hash": result.get("audit_entry_hash"),
        "approval_request_id": result.get("approval_request_id"),
        "result_summary": {
            k: v for k, v in (result.get("result") or {}).items()
            if k in ("anomaly_count", "recurring", "graph_node_count", "ranked_alternatives")
        },
    }


def _assemble_final_from_steps(steps: list[dict]) -> str:
    """Assemble a readable final summary from completed step records.

    Used when the loop force-finalizes due to repeated skill calls.
    """
    if not steps:
        return "No skills executed; intent could not be evaluated."
    parts = [
        f"{s['skill']} → {s['outcome']}"
        for s in steps
    ]
    return "Force-finalized after repeated skill selection. Results: " + "; ".join(parts) + "."


def orchestrate(
    intent: str,
    context: dict | None = None,
    max_steps: int = 6,
    threshold: float | None = None,
    audit_path: str | None = None,
    graph=None,
    llm: Callable[..., str] = call_hermes,
) -> dict:
    """Run the bounded Hermes CFO orchestration loop.

    Dispatches skills through the NemoClaw harness up to max_steps times.
    Anti-repeat guard: if the model selects the same skill+args consecutively,
    an observation is injected; on the 3rd consecutive identical call the loop
    force-finalizes with a summary assembled from prior steps.
    The llm param is dependency-injected so tests can pass a scripted planner.
    Returns intent, step trace, final summary, escalation state, and audit hashes.
    """
    # Deferred import to avoid circular dependency at module load
    from fixtures.seed_data import seed_invoices as _seed  # noqa: PLC0415

    executed_history: list[dict] = []
    messages: list[dict] = [{"role": "user", "content": f"Begin orchestration for: {intent}"}]

    steps: list[dict] = []
    audit_hashes: list[str] = []
    final_summary: str | None = None
    escalated = False
    approval_request_id: str | None = None

    # Anti-repeat state: track consecutive identical (skill, frozen-args) selections
    _last_skill_key: str | None = None
    _consecutive_count: int = 0
    _CONSECUTIVE_FORCE_FINALIZE = 3  # force-finalize on 3rd consecutive identical call

    for i in range(max_steps):  # bounded: satisfies loop-bound rule
        system_prompt = _build_system_prompt(intent, context, graph, threshold, executed_history)
        reply = llm(messages, system=system_prompt)
        action = _parse_action(reply)

        if action is None:
            final_summary = f"[orchestrator] step {i}: model output was not parseable JSON — stopping."
            break

        act_type = action.get("action", "")

        if act_type == "final":
            final_summary = action.get("summary", "")
            break

        if act_type == "escalate":
            escalated = True
            final_summary = action.get("reason", "escalated by model")
            break

        if act_type == "run_skill":
            skill_name = action.get("skill", "")
            raw_args = {k: v for k, v in action.get("args", {}).items() if v != "__SEED__"}
            skill_key = f"{skill_name}::{json.dumps(raw_args, sort_keys=True)}"

            if skill_key == _last_skill_key:
                _consecutive_count += 1
            else:
                _last_skill_key = skill_key
                _consecutive_count = 1

            if _consecutive_count >= _CONSECUTIVE_FORCE_FINALIZE:
                # Third consecutive identical call: force-finalize without re-running
                final_summary = _assemble_final_from_steps(steps)
                break

            if _consecutive_count == 2:
                # Second consecutive identical call: inject reminder, do not re-run
                obs = (
                    f"REMINDER: {skill_name} was already executed with the same args and returned "
                    f"outcome={steps[-1]['outcome'] if steps else 'unknown'}. "
                    f"Do not repeat it. Review the observations and emit {{\"action\":\"final\",...}}."
                )
                messages.append({"role": "tool", "content": obs})
                continue  # skip execution, re-prompt

            step_rec = _run_step(action, i, threshold, audit_path, _seed)
            steps.append(step_rec)
            executed_history.append({
                "skill": step_rec["skill"],
                "args": step_rec.get("args", {}),
                "outcome": step_rec["outcome"],
            })

            h = step_rec.get("audit_entry_hash")
            if h:
                audit_hashes.append(h)

            obs = (
                f"observation: step {i} skill={step_rec['skill']} "
                f"outcome={step_rec['outcome']} hash={str(h)[:12] if h else 'none'}"
            )
            messages.append({"role": "tool", "content": obs})

            if step_rec.get("outcome") == "escalated":
                escalated = True
                approval_request_id = step_rec.get("approval_request_id")
                final_summary = f"Escalated: approval required ({approval_request_id})"
                break
        else:
            final_summary = f"[orchestrator] unknown action type {act_type!r} — stopping."
            break

    return {
        "intent": intent,
        "steps": steps,
        "final": final_summary,
        "escalated": escalated,
        "approval_request_id": approval_request_id,
        "audit_hashes": audit_hashes,
    }
