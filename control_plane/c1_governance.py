"""control_plane/c1_governance.py: ConductorOne governance helper for the STR demo.

Foregrounds the C1 identity and access governance story in the demo. All identities
are synthetic and local; no real C1 work-tenant data is used here (PANW/C1 firewall,
user-level CLAUDE.md rule #3).

Data sources: public/GA ConductorOne product, OSS Baton connector, synthetic fixtures.

Public API:
    issue_nhi(agent_id, scopes, *, ttl_seconds) -> dict
        Returns a scoped non-human-identity record, labeled as ConductorOne-governed.

    authorize(nhi, action, resource) -> tuple[bool, str]
        Consults policy_check.check_policy; never raises. Returns (allowed, reason).

    access_inventory() -> dict
        Returns the crew/entitlement access view via baton_client.fetch_access.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from control_plane import baton_client, policy_check

_logger = logging.getLogger(__name__)

_C1_GOVERNANCE_SOURCE = "conductorone-synthetic-demo"


def issue_nhi(
    agent_id: str,
    scopes: list[str],
    *,
    ttl_seconds: int = 86400,
) -> dict[str, Any]:
    """Return a scoped non-human-identity record, labeled as ConductorOne-governed.

    The record is synthetic/local. It carries enough structure to demonstrate the
    ConductorOne NHI lifecycle (id, scopes, parent, expiry, governance_source).
    ttl_seconds defaults to 24h.
    """
    issued_at = int(time.time())
    expiry = issued_at + ttl_seconds
    return {
        "id": f"nhi-{agent_id}-{issued_at}",
        "agent_id": agent_id,
        "scopes": scopes,
        "parent": "conductorone://demo/str-agent-platform",
        "issued_at": issued_at,
        "expiry": expiry,
        "governance_source": _C1_GOVERNANCE_SOURCE,
        "status": "active",
    }


def authorize(
    nhi: dict[str, Any],
    action: str,
    resource: str,
) -> tuple[bool, str]:
    """Return (allowed, reason) for the NHI performing action on resource.

    Consults policy_check.check_policy with the action as vendor and a nominal
    amount of 0 (access checks are binary, not spend-gated here). Never raises.
    Falls back to a synthetic default when policy_check itself errors.
    """
    agent_id = nhi.get("agent_id", "unknown-agent")
    # Map action/resource into the policy_check vendor/amount convention.
    # Amount is 0 for access checks; the policy gate here is identity-scope-based.
    pseudo_vendor = f"{resource}:{action}"
    try:
        decision = policy_check.check_policy(
            vendor=pseudo_vendor,
            amount=0.0,
            requester=agent_id,
        )
        return decision.allowed, decision.reason
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "policy_check error for %s on %s/%s: %s (defaulting to allowed)",
            agent_id, action, resource, exc,
        )
        return True, f"synthetic default: policy_check unavailable ({exc})"


def access_inventory() -> dict[str, Any]:
    """Return the crew/entitlement access inventory via baton_client.fetch_access.

    Returns a dict with keys: grants (list of AccessGrant dicts), source (str),
    seat_summary (per-resource seat counts).
    """
    grants, source = baton_client.fetch_access()
    seat_summary = baton_client.summarize_seats(grants)
    return {
        "grants": [
            {
                "principal": g.principal,
                "resource": g.resource,
                "entitlement": g.entitlement,
                "last_used": g.last_used,
                "source_connector": g.source_connector,
            }
            for g in grants
        ],
        "source": source,
        "seat_summary": seat_summary,
    }
