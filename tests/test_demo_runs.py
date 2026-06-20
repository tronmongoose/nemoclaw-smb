"""tests/test_demo_runs.py -- Integration tests for the three-act demo runner.

Verifies that all three acts complete without exception in DEMO_MODE and that
the final audit chain verifies True. Each act is tested independently so
failures are localized.

All tests run in DEMO_MODE with no live credentials required.
"""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("DEMO_MODE", "true")


def _chain_ok() -> bool:
    """Return True when the audit chain is valid after a demo run."""
    from agent.audit_log import verify_chain
    ok, _ = verify_chain()
    return ok


def test_act_1_no_exception() -> None:
    """ACT 1 completes without raising and audit chain is valid after run."""
    from demo.run_demo import run_act_1
    run_act_1()
    assert _chain_ok(), "audit chain is invalid after Act 1"


def test_act_2_no_exception() -> None:
    """ACT 2 completes without raising and audit chain is valid after run."""
    from demo.run_demo import run_act_2
    run_act_2()
    assert _chain_ok(), "audit chain is invalid after Act 2"


def test_act_3_no_exception() -> None:
    """ACT 3 completes without raising and audit chain is valid after run."""
    from demo.run_demo import run_act_3
    run_act_3()
    assert _chain_ok(), "audit chain is invalid after Act 3"


def test_run_demo_full_no_exception() -> None:
    """Full three-act demo (run_demo) completes without raising."""
    from demo.run_demo import run_demo
    run_demo()  # raises RuntimeError on audit chain failure


def test_run_demo_audit_chain_verifies() -> None:
    """After a full run_demo call, verify_chain returns True."""
    from demo.run_demo import run_demo
    from agent.audit_log import verify_chain
    run_demo()
    ok, detail = verify_chain()
    assert ok, f"audit chain did not verify after full demo: {detail}"
