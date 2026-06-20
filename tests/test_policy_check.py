"""Tests for control_plane/policy_check.py.

policy_mock.yaml: Adobe limit 400, AWS limit 1500, default 1000.
Note: vendor key in YAML is "Adobe" not "Adobe Creative Cloud" — unknown vendor
names fall through to the default_limit path.
"""

import pytest
import yaml

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
# C1_API_KEY present -> graceful fallback to local policy (no C1 client wired)
# ---------------------------------------------------------------------------

def test_c1_backend_falls_back_when_key_present(monkeypatch):
    """C1_API_KEY set but no real client wired; must not raise and must return a valid decision."""
    monkeypatch.setenv("C1_API_KEY", "test-key")
    decision = check_policy("Adobe", 340.0)
    assert decision.allowed is True
    assert decision.limit == 400.0


def test_c1_backend_fallback_denied_when_over_limit(monkeypatch):
    """C1 fallback still enforces local policy limits."""
    monkeypatch.setenv("C1_API_KEY", "test-key")
    decision = check_policy("Adobe", 500.0)
    assert decision.allowed is False
    assert decision.limit == 400.0


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


# ---------------------------------------------------------------------------
# Per-tenant policy path
# ---------------------------------------------------------------------------

def _write_custom_policy(tmp_path, vendor: str, limit: float) -> str:
    """Write a minimal custom policy YAML and return its path string."""
    policy = {
        "vendors": {vendor: {"monthly_limit": limit}},
        "default_limit": 9999,
        "blocked_vendors": [],
    }
    p = tmp_path / "custom_policy.yaml"
    p.write_text(yaml.dump(policy))
    return str(p)


def test_custom_policy_path_kwarg_changes_decision(tmp_path):
    """A policy_path kwarg pointing to a custom file overrides the bundled mock."""
    # Custom policy allows SpecialVendor up to $5000; bundled mock default is $1000.
    path = _write_custom_policy(tmp_path, "SpecialVendor", 5000.0)
    decision = check_policy("SpecialVendor", 3000.0, policy_path=path)
    assert decision.allowed is True
    assert decision.limit == pytest.approx(5000.0)


def test_custom_policy_path_kwarg_blocks_above_custom_limit(tmp_path):
    """Custom policy correctly denies amounts above its own limit."""
    path = _write_custom_policy(tmp_path, "SpecialVendor", 200.0)
    decision = check_policy("SpecialVendor", 500.0, policy_path=path)
    assert decision.allowed is False


def test_absent_policy_path_uses_bundled_mock(monkeypatch):
    """When policy_path kwarg is absent and env is unset, bundled mock applies."""
    monkeypatch.delenv("NEMOCLAW_POLICY_PATH", raising=False)
    decision = check_policy("Adobe", 340.0)
    # Bundled mock: Adobe limit 400
    assert decision.allowed is True
    assert decision.limit == pytest.approx(400.0)


def test_policy_path_env_override(tmp_path, monkeypatch):
    """NEMOCLAW_POLICY_PATH env is honored when no kwarg is passed."""
    path = _write_custom_policy(tmp_path, "EnvVendor", 1500.0)
    monkeypatch.setenv("NEMOCLAW_POLICY_PATH", path)
    decision = check_policy("EnvVendor", 1200.0)
    assert decision.allowed is True
    assert decision.limit == pytest.approx(1500.0)
