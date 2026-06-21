"""tests/test_control_plane_live.py: live + offline tests for Baton-backed authorize.

The live test runs only when carryall_baton + authority_runtime are importable and
CARRYALL_BATON_C1Z points at a real .c1z. It asserts authorize() returns a real
grant-matched decision sourced from 'baton-carryall'. It skips cleanly otherwise,
so `pytest tests/` stays green without the optional packages or a c1z.

The offline test asserts authorize() falls back to the synthetic source and never
raises when no Baton route or .c1z is in play. It always runs.

No ConductorOne SaaS tenant is required by either test (the C1 SaaS is off the
authorize path).
"""
from __future__ import annotations

import pytest

from control_plane.c1_governance import AuthorizeResult, authorize, issue_nhi


def _baton_importable() -> bool:
    """Return True when both authority_runtime and carryall_baton import."""
    try:
        import authority_runtime  # noqa: F401
        import carryall_baton  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Live: real BatonBackend.check_access against a .c1z from CARRYALL_BATON_C1Z
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_authorize_live_baton_source(tmp_path, monkeypatch) -> None:
    """authorize() returns a baton-carryall grant decision against a real .c1z."""
    if not _baton_importable():
        pytest.skip("authority_runtime / carryall_baton not installed")

    from control_plane.c1z_fixtures import generate_c1z

    c1z = generate_c1z(tmp_path / "live_str_org.c1z")
    monkeypatch.setenv("CARRYALL_BATON_C1Z", c1z)

    nhi = issue_nhi("str-platform-agent", ["str:price", "str:aeo-audit"])
    result = authorize(nhi, "price", "str-platform")

    assert isinstance(result, AuthorizeResult)
    assert result.source == "baton-carryall"
    assert result.allowed is True
    assert "str-platform-agent" in result.reason


@pytest.mark.live
def test_authorize_live_cleaner_card_grant(tmp_path, monkeypatch) -> None:
    """The cleaner-subagent's card:issue:cleaning grant is matched for real."""
    if not _baton_importable():
        pytest.skip("authority_runtime / carryall_baton not installed")

    from control_plane.c1z_fixtures import generate_c1z

    c1z = generate_c1z(tmp_path / "live_str_org.c1z")
    monkeypatch.setenv("CARRYALL_BATON_C1Z", c1z)

    nhi = issue_nhi("cleaner-subagent", ["card:issue:cleaning"])
    result = authorize(nhi, "card:issue", "stripe-issuing")

    assert result.source == "baton-carryall"
    assert result.allowed is True


@pytest.mark.live
def test_authorize_live_denies_ungranted_action(tmp_path, monkeypatch) -> None:
    """An action with no matching baton grant is denied, still source baton-carryall."""
    if not _baton_importable():
        pytest.skip("authority_runtime / carryall_baton not installed")

    from control_plane.c1z_fixtures import generate_c1z

    c1z = generate_c1z(tmp_path / "live_str_org.c1z")
    monkeypatch.setenv("CARRYALL_BATON_C1Z", c1z)

    # str-platform-agent has no grant whose entitlement ends ':aeo-audit' on cards.
    nhi = issue_nhi("cleaner-subagent", ["card:issue:cleaning"])
    result = authorize(nhi, "aeo-audit", "str-platform")

    assert result.source == "baton-carryall"
    assert result.allowed is False


# ---------------------------------------------------------------------------
# Offline: synthetic fallback, never raises
# ---------------------------------------------------------------------------

def test_authorize_offline_falls_back_to_synthetic() -> None:
    """An unmapped (action, resource) returns the synthetic source and never raises."""
    nhi = issue_nhi("str-owner-agent", ["stripe:payout"])
    result = authorize(nhi, "propose_payment", "stripe")
    assert isinstance(result, AuthorizeResult)
    assert result.source == "synthetic"
    assert isinstance(result.allowed, bool)
    assert isinstance(result.reason, str)


def test_authorize_offline_no_c1z_falls_back(monkeypatch) -> None:
    """A mapped route with no resolvable .c1z falls back to synthetic, never raises."""
    monkeypatch.setattr(
        "control_plane.c1_governance._resolve_c1z_path", lambda: None
    )
    nhi = issue_nhi("str-platform-agent", ["str:price"])
    result = authorize(nhi, "price", "str-platform")
    assert result.source == "synthetic"
    assert isinstance(result.allowed, bool)


def test_authorize_offline_package_absent_falls_back(monkeypatch) -> None:
    """A mapped route falls back to synthetic when the baton attempt yields None."""
    monkeypatch.setattr(
        "control_plane.c1_governance._baton_authorize",
        lambda nhi, action, resource: None,
    )
    nhi = issue_nhi("str-platform-agent", ["str:price"])
    result = authorize(nhi, "price", "str-platform")
    assert result.source == "synthetic"
    assert isinstance(result.reason, str)


def test_authorize_result_backward_compatible_tuple() -> None:
    """AuthorizeResult unpacks as (allowed, reason) and indexes like a 2-tuple."""
    nhi = issue_nhi("a", ["x:y"])
    result = authorize(nhi, "read", "ledger")
    assert len(result) == 2
    allowed, reason = result
    assert isinstance(allowed, bool)
    assert isinstance(reason, str)
    assert result[0] == allowed
    assert result[1] == reason
    assert result["allowed"] == allowed
    assert result["source"] in ("baton-carryall", "synthetic")
