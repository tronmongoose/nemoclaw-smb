"""Vendor/amount authorization gate. Mock-backed by default; C1 backend gated on API key presence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_POLICY_PATH = Path(__file__).parent / "policy_mock.yaml"


@dataclass
class PolicyDecision:
    """Result of a single policy evaluation."""

    allowed: bool
    reason: str
    limit: float | None


def _load_policy() -> dict[str, Any]:
    """Load policy config from NEMOCLAW_POLICY_PATH or the bundled mock."""
    path = Path(os.environ.get("NEMOCLAW_POLICY_PATH", str(_DEFAULT_POLICY_PATH)))
    with path.open() as fh:
        return yaml.safe_load(fh)


def _mock_check(vendor: str, amount: float, policy: dict[str, Any]) -> PolicyDecision:
    """Evaluate vendor/amount against the local YAML policy config."""
    blocked: list[str] = policy.get("blocked_vendors", [])
    if vendor in blocked:
        return PolicyDecision(allowed=False, reason=f"{vendor} is on the blocked-vendor list", limit=None)

    vendors: dict[str, Any] = policy.get("vendors", {})
    default_limit: float = float(policy.get("default_limit", 1000))

    if vendor in vendors:
        limit = float(vendors[vendor]["monthly_limit"])
        if amount <= limit:
            return PolicyDecision(allowed=True, reason=f"{vendor} approved: ${amount} within ${limit} monthly limit", limit=limit)
        return PolicyDecision(allowed=False, reason=f"{vendor} denied: ${amount} exceeds ${limit} monthly limit", limit=limit)

    # Unknown vendor falls through to default
    #COMPLETION_DRIVE: unknown vendors are not blocked by default, only capped at default_limit
    if amount <= default_limit:
        return PolicyDecision(allowed=True, reason=f"Unknown vendor '{vendor}' approved: ${amount} within default ${default_limit} limit", limit=default_limit)
    return PolicyDecision(allowed=False, reason=f"Unknown vendor '{vendor}' denied: ${amount} exceeds default ${default_limit} limit", limit=default_limit)


def _c1_check(vendor: str, amount: float, requester: str) -> PolicyDecision:
    """ConductorOne policy backend — ships disabled; raises until a C1 API key is sanctioned."""
    raise NotImplementedError("ConductorOne backend gated on C1 blessing")


def check_policy(vendor: str, amount: float, requester: str = "agent") -> PolicyDecision:
    """Primary entry point. Delegates to C1 if C1_API_KEY is present, otherwise uses the mock."""
    if os.environ.get("C1_API_KEY"):
        return _c1_check(vendor, amount, requester)
    policy = _load_policy()
    return _mock_check(vendor, amount, policy)
