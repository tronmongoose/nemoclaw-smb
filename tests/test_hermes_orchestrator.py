"""
test_hermes_orchestrator.py — Offline tests for hermes_client and hermes_orchestrator.

Tests:
  - call_hermes returns scripted mock string when NOUS_PORTAL_API_KEY is absent
  - orchestrate dispatches through the harness (audit hash present, chain verifies)
  - spend above threshold returns escalated=True with approval_request_id, stops loop
  - max_steps is respected: always-run_skill llm terminates after max_steps
  - malformed model output finalizes gracefully without exception
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

import pytest

from agent.audit_log import verify_chain
from agent.hermes_client import _MOCK_PREFIX, call_hermes
from agent.hermes_orchestrator import _parse_action, orchestrate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def audit_path(tmp_path: pathlib.Path) -> str:
    """Return a fresh audit file path in a temp dir."""
    return str(tmp_path / "audit.jsonl")


# ---------------------------------------------------------------------------
# call_hermes — no-key mock
# ---------------------------------------------------------------------------


def test_call_hermes_no_key_returns_mock(monkeypatch):
    """call_hermes returns a '[hermes-mock] ' prefixed string when key is absent."""
    monkeypatch.delenv("NOUS_PORTAL_API_KEY", raising=False)
    result = call_hermes([{"role": "user", "content": "hello"}])
    assert result.startswith(_MOCK_PREFIX)


def test_call_hermes_no_key_does_not_raise(monkeypatch):
    """call_hermes never raises even with no key and no network."""
    monkeypatch.delenv("NOUS_PORTAL_API_KEY", raising=False)
    result = call_hermes([])
    assert isinstance(result, str)


def test_call_hermes_mock_advances_with_observation_turns(monkeypatch):
    """Scripted mock returns step 1 when one observation turn is present."""
    monkeypatch.delenv("NOUS_PORTAL_API_KEY", raising=False)
    messages = [
        {"role": "user", "content": "start"},
        {"role": "tool", "content": "observation: step 0 outcome=executed"},
    ]
    result = call_hermes(messages)
    assert result.startswith(_MOCK_PREFIX)
    # Step 1 mock is invoice_ingest_skill
    assert "invoice_ingest_skill" in result


# ---------------------------------------------------------------------------
# _parse_action
# ---------------------------------------------------------------------------


def test_parse_action_clean_json():
    """_parse_action extracts a clean JSON dict."""
    raw = json.dumps({"action": "final", "summary": "done"})
    result = _parse_action(raw)
    assert result == {"action": "final", "summary": "done"}


def test_parse_action_with_prose():
    """_parse_action finds JSON embedded in surrounding prose."""
    raw = 'Sure, here is my action: {"action": "final", "summary": "ok"} Hope that helps.'
    result = _parse_action(raw)
    assert result is not None
    assert result["action"] == "final"


def test_parse_action_with_mock_prefix():
    """_parse_action strips the [hermes-mock] prefix before parsing."""
    raw = '[hermes-mock] {"action": "final", "summary": "mock done"}'
    result = _parse_action(raw)
    assert result is not None
    assert result["action"] == "final"


def test_parse_action_malformed_returns_none():
    """_parse_action returns None on non-JSON input."""
    assert _parse_action("this is not json at all") is None
    assert _parse_action("") is None


# ---------------------------------------------------------------------------
# orchestrate — happy path
# ---------------------------------------------------------------------------


def _make_llm_sequence(*actions: dict):
    """Return a fake llm that yields actions in order then returns final."""
    calls = list(actions)
    final = {"action": "final", "summary": "scripted done"}
    idx = [0]

    def fake_llm(messages, *, system=None, **_):
        i = idx[0]
        idx[0] += 1
        if i < len(calls):
            return json.dumps(calls[i])
        return json.dumps(final)

    return fake_llm


def test_orchestrate_dispatches_through_harness(audit_path: str, monkeypatch):
    """orchestrate dispatches skill through harness; audit hash present and chain verifies."""
    monkeypatch.setenv("NEMOCLAW_AUDIT_PATH", audit_path)

    llm = _make_llm_sequence(
        {
            "action": "run_skill",
            "skill": "invoice_ingest_skill",
            "args": {"invoices": []},
            "reason": "test",
        }
    )

    result = orchestrate(
        intent="test dispatch",
        llm=llm,
        audit_path=audit_path,
        max_steps=4,
    )

    assert result["escalated"] is False
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["skill"] == "invoice_ingest_skill"
    assert step["outcome"] == "executed"
    assert step["audit_entry_hash"] is not None
    assert len(result["audit_hashes"]) == 1

    ok, msg = verify_chain(audit_path)
    assert ok, f"audit chain broken: {msg}"


def test_orchestrate_returns_step_trace_and_final(audit_path: str):
    """orchestrate returns intent, steps, and final summary in the result dict."""
    llm = _make_llm_sequence(
        {"action": "run_skill", "skill": "invoice_ingest_skill", "args": {"invoices": []}, "reason": "r"},
    )
    result = orchestrate(intent="trace test", llm=llm, audit_path=audit_path, max_steps=4)

    assert result["intent"] == "trace test"
    assert isinstance(result["steps"], list)
    assert result["final"] is not None


# ---------------------------------------------------------------------------
# orchestrate — escalation
# ---------------------------------------------------------------------------


def test_orchestrate_escalates_on_spend_above_threshold(audit_path: str, monkeypatch):
    """spend above threshold returns escalated=True with approval_request_id; no further steps."""
    approvals_dir = pathlib.Path(audit_path).parent / "approvals"
    approvals_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("NEMOCLAW_APPROVALS_DIR", str(approvals_dir))
    monkeypatch.setenv("NEMOCLAW_AUDIT_PATH", audit_path)

    # Patch execute in the orchestrator module's namespace (where it was imported to).
    from unittest.mock import patch
    import agent.hermes_orchestrator as _orch_mod

    escalated_result = {
        "skill": "invoice_ingest_skill",
        "outcome": "escalated",
        "steps": [],
        "result": None,
        "audit_entry_hash": "aabbccaabbccaabbccaabbccaabbccaabbccaabbccaabbccaabbccaabbccaabb",
        "approval_request_id": "req-test-123",
    }

    llm = _make_llm_sequence(
        {"action": "run_skill", "skill": "invoice_ingest_skill", "args": {"invoices": []}, "reason": "test escalate"},
    )

    with patch.object(_orch_mod, "execute", return_value=escalated_result):
        result = orchestrate(
            intent="big spend",
            llm=llm,
            threshold=100.0,
            audit_path=audit_path,
            max_steps=4,
        )

    assert result["escalated"] is True
    assert result["approval_request_id"] == "req-test-123"
    # No further steps after escalation
    assert len(result["steps"]) == 1


# ---------------------------------------------------------------------------
# orchestrate — max_steps bound
# ---------------------------------------------------------------------------


def test_orchestrate_respects_max_steps(audit_path: str):
    """An llm that always returns run_skill terminates after max_steps; no infinite loop."""
    MAX = 3

    def always_run_skill(messages, *, system=None, **_):
        return json.dumps({"action": "run_skill", "skill": "invoice_ingest_skill", "args": {"invoices": []}, "reason": "loop"})

    result = orchestrate(intent="loop test", llm=always_run_skill, audit_path=audit_path, max_steps=MAX)
    assert len(result["steps"]) == MAX
    assert result["final"] is None  # no explicit final action was issued


# ---------------------------------------------------------------------------
# orchestrate — malformed output
# ---------------------------------------------------------------------------


def test_orchestrate_malformed_output_finalizes_gracefully(audit_path: str):
    """Non-JSON model output finalizes with an error note; no exception raised."""
    def bad_llm(messages, *, system=None, **_):
        return "I cannot decide what to do here. Please advise."

    result = orchestrate(intent="bad output test", llm=bad_llm, audit_path=audit_path, max_steps=3)
    assert result["escalated"] is False
    assert result["final"] is not None
    assert len(result["steps"]) == 0
