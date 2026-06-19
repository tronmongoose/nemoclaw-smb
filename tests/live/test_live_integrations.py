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
