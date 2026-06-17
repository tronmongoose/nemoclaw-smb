"""Tests for control_plane/policy_check.py.

policy_mock.yaml: Adobe limit 400, AWS limit 1500, default 1000.
Note: vendor key in YAML is "Adobe" not "Adobe Creative Cloud" — unknown vendor
names fall through to the default_limit path.
"""

import pytest

from control_plane.policy_check import check_policy


@pytest.fixture(autouse=True)
def clear_c1_api_key(monkeypatch):
    """Ensure C1 backend is never invoked; mock path is always used."""
    monkeypatch.delenv("C1_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# Adobe (exact YAML key) - limit 400
# ---------------------------------------------------------------------------

def test_adobe_340_allowed():
    decision = check_policy("Adobe", 340.0)
    assert decision.allowed is True
    assert decision.limit == 400.0


def test_adobe_500_denied():
    decision = check_policy("Adobe", 500.0)
    assert decision.allowed is False
    assert decision.limit == 400.0


def test_adobe_400_allowed_at_limit():
    # Boundary: amount == limit is allowed (<=)
    decision = check_policy("Adobe", 400.0)
    assert decision.allowed is True


def test_adobe_401_denied_above_limit():
    decision = check_policy("Adobe", 401.0)
    assert decision.allowed is False


# ---------------------------------------------------------------------------
# Unknown vendor -> default limit 1000
# ---------------------------------------------------------------------------

def test_unknown_vendor_under_default_allowed():
    decision = check_policy("SomeNewSaas", 500.0)
    assert decision.allowed is True
    assert decision.limit == 1000.0


def test_unknown_vendor_over_default_denied():
    decision = check_policy("SomeNewSaas", 1500.0)
    assert decision.allowed is False
    assert decision.limit == 1000.0


def test_unknown_vendor_at_default_limit_allowed():
    decision = check_policy("SomeNewSaas", 1000.0)
    assert decision.allowed is True


# ---------------------------------------------------------------------------
# C1_API_KEY present -> raises NotImplementedError (gated backend)
# ---------------------------------------------------------------------------

def test_c1_backend_raises_when_key_present(monkeypatch):
    monkeypatch.setenv("C1_API_KEY", "test-key")
    with pytest.raises(NotImplementedError):
        check_policy("Adobe", 340.0)


# ---------------------------------------------------------------------------
# PolicyDecision shape
# ---------------------------------------------------------------------------

def test_decision_has_reason_string():
    decision = check_policy("Adobe", 340.0)
    assert isinstance(decision.reason, str)
    assert len(decision.reason) > 0


def test_decision_reason_references_vendor():
    decision = check_policy("Adobe", 500.0)
    assert "Adobe" in decision.reason
