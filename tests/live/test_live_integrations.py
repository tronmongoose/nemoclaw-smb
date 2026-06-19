"""
test_live_integrations.py — Rule-#10 layer: tests that FAIL when a live integration breaks.

Each test skips (not fails, not errors) when the required key or binary is absent.
All tests are marked @pytest.mark.live so they can be filtered with -m live.

Run all:  pytest tests/live/ -m live -v
Skip all: pytest tests/ (live tests auto-skip when unkeyed)
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest


pytestmark = pytest.mark.live


# ---------------------------------------------------------------------------
# Hermes
# ---------------------------------------------------------------------------

def test_hermes_live() -> None:
    """Real Hermes call must return a non-mock response when keyed."""
    from agent.hermes_client import _MOCK_PREFIX, call_hermes, hermes_available

    if not hermes_available():
        pytest.skip("NOUS_PORTAL_API_KEY not set")

    result = call_hermes([{"role": "user", "content": "reply PONG"}], max_tokens=8)
    assert not result.startswith(_MOCK_PREFIX), (
        f"Hermes returned mock response when key is set: {result!r}"
    )
    assert len(result.strip()) > 0, "Hermes returned empty response"


# ---------------------------------------------------------------------------
# Nemotron
# ---------------------------------------------------------------------------

def test_nemotron_live() -> None:
    """Real Nemotron call must return a non-mock response when keyed."""
    from agent.nvidia_client import _MOCK_PREFIX, call_nemotron, nemotron_available

    if not nemotron_available():
        pytest.skip("NVIDIA_NIM_API_KEY not set")

    result = call_nemotron("reply PONG", max_tokens=8)
    assert not result.startswith(_MOCK_PREFIX), (
        f"Nemotron returned mock response when key is set: {result!r}"
    )
    assert len(result.strip()) > 0, "Nemotron returned empty response"


# ---------------------------------------------------------------------------
# Stripe SDK (test-mode balance read)
# ---------------------------------------------------------------------------

def test_stripe_live() -> None:
    """Stripe test-mode Balance.retrieve() must succeed when sk_test_ key is set."""
    from payments.stripe_client import _get_stripe, _is_live_key

    key = __import__("os").environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        pytest.skip("STRIPE_SECRET_KEY not set")
    if _is_live_key(key):
        pytest.skip("Live-mode key present; NemoClaw refuses live-mode — skipping")

    stripe = _get_stripe()
    if stripe is None:
        pytest.skip("stripe SDK not importable or key not test-mode")

    bal = stripe.Balance.retrieve()
    assert "available" in bal, f"Balance.retrieve() response missing 'available': {bal}"
    assert isinstance(bal["available"], list), "balance.available is not a list"


# ---------------------------------------------------------------------------
# Baton
# ---------------------------------------------------------------------------

def test_guardrails_live() -> None:
    """Real NeMo Guardrails LLM check must return a decision (not crash/fallback) when keyed."""
    import os

    if os.environ.get("NEMOCLAW_GUARDRAILS") != "1":
        pytest.skip("NEMOCLAW_GUARDRAILS != 1")
    if not os.environ.get("NOUS_PORTAL_API_KEY"):
        pytest.skip("NOUS_PORTAL_API_KEY not set")
    try:
        import nemoguardrails  # noqa: F401
    except ImportError:
        pytest.skip("nemoguardrails not installed")

    from agent.nemoclaw_harness import _nemo_guardrails_check

    allowed, reason = _nemo_guardrails_check("onboarding_skill", {}, (True, "fallback"))
    # The rail must return a real string from the LLM, not the static fallback.
    assert reason != "fallback", f"got static fallback — LLM call did not execute: {reason!r}"
    assert isinstance(allowed, bool)
    assert len(reason) > 0


def test_sandbox_subprocess_live() -> None:
    """Subprocess sandbox must run a serializable skill in a child process and round-trip JSON."""
    import json
    import os

    sandbox_val = os.environ.get("NEMOCLAW_SANDBOX", "").strip().lower()
    if sandbox_val not in ("1", "true", "yes", "on"):
        pytest.skip("NEMOCLAW_SANDBOX not truthy")

    # Force skill registration before calling _run_skill
    import agent.skills.onboarding_skill  # noqa: F401
    from agent.nemoclaw_harness import _run_skill

    result, label = _run_skill("onboarding_skill", {})

    assert label == "subprocess", (
        f"expected subprocess sandbox label, got {label!r}"
    )
    assert isinstance(result, dict), f"subprocess result not a dict: {result!r}"
    assert "node_count" in result, f"expected node_count in result: {result}"
    # Verify JSON round-trip: result must be serializable (it came from JSON parse)
    serialized = json.dumps(result)
    assert json.loads(serialized) == result


def test_c1_policy_check_live() -> None:
    """Real C1 token exchange + grant check must succeed when C1_API_KEY and C1_BASE_URL are set.

    Required env vars:
        C1_API_KEY        — C1 client ID
        C1_API_SECRET     — C1 versioned Ed25519 client secret
        C1_BASE_URL       — tenant URL (e.g. "https://acme.conductor.one")
    Optional:
        C1_VENDOR_APP_ID, C1_VENDOR_ENTITLEMENT_ID — triggers a real grant check when set.

    FIREWALL: point at a synthetic SMB test tenant only, never a production work tenant.
    """
    import os
    from control_plane.c1_client import C1ClientError, c1_configured, fetch_c1_token

    if not os.environ.get("C1_API_KEY") or not os.environ.get("C1_BASE_URL"):
        pytest.skip("C1_API_KEY or C1_BASE_URL not set")

    client_id = os.environ["C1_API_KEY"]
    client_secret = os.environ.get("C1_API_SECRET", client_id)
    base_url = os.environ["C1_BASE_URL"]

    try:
        token = fetch_c1_token(client_id, client_secret, base_url)
    except C1ClientError as exc:
        pytest.fail(f"C1 token exchange failed: {exc}")

    assert isinstance(token, str) and len(token) > 0, (
        "fetch_c1_token returned an empty or non-string token"
    )

    from control_plane.c1_client import check_policy_c1
    try:
        result = check_policy_c1("TestVendor", 100.0, "live-test-user")
    except C1ClientError as exc:
        pytest.fail(f"check_policy_c1 raised C1ClientError on a live tenant: {exc}")

    assert hasattr(result, "allowed"), "PolicyDecision missing 'allowed' attribute"
    assert isinstance(result.reason, str) and len(result.reason) > 0


def test_baton_live() -> None:
    """baton --version must exit 0 when the binary is on PATH."""
    import subprocess

    from control_plane.baton_client import baton_available

    if not baton_available():
        pytest.skip("baton binary not on PATH")

    result = subprocess.run(
        ["baton", "--version"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, (
        f"baton --version exited {result.returncode}: {result.stderr.strip()}"
    )
    assert result.stdout.strip(), "baton --version produced no output"


# ---------------------------------------------------------------------------
# GBrain MCP (real write+read round-trip)
# ---------------------------------------------------------------------------

def test_gbrain_live() -> None:
    """Real GBrain write+read round-trip when GBRAIN_MCP_CMD is set.

    Required env:
        GBRAIN_MCP_CMD — command to launch the GBrain stdio MCP server.
          #SUGGEST_VERIFY: once bun is installed, the expected value is:
            GBRAIN_MCP_CMD="bun /path/to/gbrain/src/cli.ts serve"
          After `npm install -g github:garrytan/gbrain` and bun on PATH:
            GBRAIN_MCP_CMD="gbrain serve"

    The test writes a probe vendor page and reads it back, asserting the
    expected content is present. This validates the full put_page -> get_page
    round-trip through the real GBrain MCP server.
    """
    import os

    from gbrain.gbrain_client import (
        GBrainError,
        gbrain_available,
        read_page,
        write_vendor_page,
    )

    if not os.environ.get("GBRAIN_MCP_CMD"):
        pytest.skip("GBRAIN_MCP_CMD not set")

    if not gbrain_available():
        pytest.skip("mcp package not importable")

    probe_label = "Live Test Probe Vendor"
    probe_key = "live-test-probe"
    probe_slug = f"nemoclaw/vendors/{probe_key}"

    try:
        write_vendor_page(probe_key, probe_label, "probe")
    except GBrainError as exc:
        pytest.fail(f"write_vendor_page failed: {exc}")

    try:
        content = read_page(probe_slug)
    except GBrainError as exc:
        pytest.fail(f"read_page failed after write: {exc}")

    assert content is not None, f"read_page returned None for slug {probe_slug!r}"
    assert probe_label in content, (
        f"Expected {probe_label!r} in page content; got: {content[:200]!r}"
    )
