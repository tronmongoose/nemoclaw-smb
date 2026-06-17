"""Tests for agent/claw_router.py.

Covers: classify_complexity tier assignment, decide_route model selection,
and log_route_decision safety (no raise, no raw task text in log).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.claw_router import (
    DEVSTRAL_MODEL,
    HERMES_MODEL,
    NEMOTRON_MODEL,
    classify_complexity,
    decide_route,
    log_route_decision,
    RouteDecision,
)


# ---------------------------------------------------------------------------
# classify_complexity — tier assignment
# ---------------------------------------------------------------------------

def test_routine_task_returns_routine_tier():
    """Categorization-only task should score below the heavy threshold."""
    result = classify_complexity("categorize these vendor invoices by type")
    assert result["tier"] == "routine"


def test_heavy_task_returns_heavy_tier():
    """Root-cause + comparison task should accumulate enough heavy signals."""
    result = classify_complexity(
        "analyze why our cloud spend increased and compare top vendors on price"
    )
    assert result["tier"] == "heavy"


def test_code_task_returns_code_tier():
    """Webhook keyword short-circuits to code regardless of other signals."""
    result = classify_complexity("write a webhook to push invoices to QuickBooks API")
    assert result["tier"] == "code"


def test_code_tier_score_is_zero():
    """Code tier always reports score 0.0 (code signals bypass arithmetic)."""
    result = classify_complexity("build an API integration for invoice export")
    assert result["score"] == 0.0


def test_routine_task_has_reasons_list():
    """classify_complexity always returns a reasons list (may be empty)."""
    result = classify_complexity("tag these transactions")
    assert isinstance(result["reasons"], list)


def test_heavy_task_has_positive_reasons():
    """Heavy signals should produce at least one positive-weight reason entry."""
    result = classify_complexity("investigate the anomaly and recommend a fix")
    assert any(r.startswith("+") for r in result["reasons"])


# ---------------------------------------------------------------------------
# decide_route — model assignment per tier
# ---------------------------------------------------------------------------

def test_decide_route_routine_returns_hermes(tmp_path):
    """Routine task routes to the Hermes model constant."""
    decision = decide_route("categorize this vendor spend bucket")
    assert decision.model == HERMES_MODEL


def test_decide_route_heavy_returns_nemotron(tmp_path):
    """Heavy task routes to the Nemotron model constant."""
    decision = decide_route(
        "analyze why our SaaS spend spiked and draft a negotiation brief"
    )
    assert decision.model == NEMOTRON_MODEL


def test_decide_route_code_returns_devstral(tmp_path):
    """Code task routes to the Devstral model constant."""
    decision = decide_route("write an API pipeline to import invoices")
    assert decision.model == DEVSTRAL_MODEL


def test_decide_route_returns_route_decision_type():
    """decide_route returns a RouteDecision instance."""
    assert isinstance(decide_route("tag vendor invoices"), RouteDecision)


# ---------------------------------------------------------------------------
# log_route_decision — never raises, never writes raw task text
# ---------------------------------------------------------------------------

def test_log_route_decision_never_raises(tmp_path):
    """log_route_decision must not raise even with an unusual path."""
    decision = RouteDecision(tier="routine", model=HERMES_MODEL, score=0.25, reasons=[])
    log_route_decision(decision, path=str(tmp_path / "decisions.jsonl"))


def test_log_route_decision_writes_jsonl_record(tmp_path):
    """log_route_decision appends a parseable JSONL record."""
    log_path = tmp_path / "decisions.jsonl"
    decision = RouteDecision(tier="heavy", model=NEMOTRON_MODEL, score=0.65, reasons=["r1", "r2"])
    log_route_decision(decision, path=str(log_path))
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["tier"] == "heavy"
    assert record["model"] == NEMOTRON_MODEL


def test_log_route_decision_does_not_store_raw_task(tmp_path):
    """The logged JSONL record must not contain the original task text."""
    log_path = tmp_path / "decisions.jsonl"
    task_text = "very secret task: analyze vendor spend in detail"
    decision = decide_route(task_text)
    # Override path so we control where it lands.
    log_route_decision(decision, path=str(log_path))
    raw = log_path.read_text()
    assert task_text not in raw
    assert "secret" not in raw


def test_log_route_decision_disabled_by_env(tmp_path, monkeypatch):
    """When NEMOCLAW_DECISION_LOG=off, no file is written."""
    monkeypatch.setenv("NEMOCLAW_DECISION_LOG", "off")
    log_path = tmp_path / "should_not_exist.jsonl"
    decision = RouteDecision(tier="routine", model=HERMES_MODEL, score=0.25, reasons=[])
    log_route_decision(decision, path=str(log_path))
    assert not log_path.exists()
