"""control_plane/c1_governance.py: Carryall + Baton governance for the STR demo.

Reframed onto OSS Baton + Erik's carryall-baton-backend + authority-runtime, with
NO ConductorOne SaaS dependency. authorize() routes through
carryall_baton.BatonBackend.check_access against a real Baton .c1z entitlement
graph when the package and a .c1z are available, and falls back to a synthetic
policy decision otherwise. A missing C1 tenant is never a blocker: the authorize
path imports no c1_client (the C1 SaaS) at all.

All identities are synthetic and local; no real C1 work-tenant data is used here
(PANW/C1 firewall, user-level CLAUDE.md rule #3).

Public API:
    issue_nhi(agent_id, scopes, *, ttl_seconds) -> dict
        Returns a scoped non-human-identity record. Unchanged.

    authorize(nhi, action, resource) -> AuthorizeResult
        Decision via BatonBackend.check_access when possible, else synthetic.
        AuthorizeResult unpacks as (allowed, reason) for backward compatibility
        and also exposes .allowed, .reason, .source and ["allowed"]/["reason"]/
        ["source"]. source is 'baton-carryall' or 'synthetic'. Never raises.

    access_inventory() -> dict
        Returns the crew/entitlement access view via baton_client.fetch_access.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from control_plane import baton_client, policy_check

_logger = logging.getLogger(__name__)

_C1_GOVERNANCE_SOURCE = "conductorone-synthetic-demo"
_SOURCE_BATON = "baton-carryall"
_SOURCE_SYNTHETIC = "synthetic"

# (action, resource) -> (slos uri, baton_action). baton_action is the action passed
# to check_access; it must equal the last ':'-segment of the granting entitlement's
# external_id in the .c1z (verified against carryall_baton 0.1.0 _action_matches).
_RESOURCE_ROUTES: dict[tuple[str, str], tuple[str, str]] = {
    ("price", "str-platform"): ("slos://vaults/platform/str", "price"),
    ("aeo-audit", "str-platform"): ("slos://vaults/platform/str", "aeo-audit"),
    ("card:issue", "stripe-issuing"): ("slos://vaults/cards/cleaning", "cleaning"),
}


class AuthorizeResult(tuple):  # noqa: SLOT000
    """A (allowed, reason) 2-tuple that also carries a labeled source.

    Backward compatible: unpacks as (allowed, reason), len()==2, [0]/[1] index.
    Additive: .allowed/.reason/.source attributes and ['allowed']/['reason']/
    ['source'] string-key access.
    """

    def __new__(cls, allowed: bool, reason: str, source: str) -> AuthorizeResult:
        """Build the 2-tuple body and attach the labeled fields."""
        obj = super().__new__(cls, (allowed, reason))
        obj._source = source
        return obj

    @property
    def allowed(self) -> bool:
        """Whether the action is authorized."""
        return self[0]

    @property
    def reason(self) -> str:
        """Human-readable reason for the decision."""
        return self[1]

    @property
    def source(self) -> str:
        """Decision source: 'baton-carryall' or 'synthetic'."""
        return self._source

    def __getitem__(self, key: Any) -> Any:
        """Support both positional (0/1) and string-key (allowed/reason/source) access."""
        if key == "allowed":
            return self[0]
        if key == "reason":
            return self[1]
        if key == "source":
            return self._source
        return super().__getitem__(key)


def issue_nhi(
    agent_id: str,
    scopes: list[str],
    *,
    ttl_seconds: int = 86400,
) -> dict[str, Any]:
    """Return a scoped non-human-identity record, labeled as ConductorOne-governed.

    The record is synthetic/local. It carries enough structure to demonstrate the
    NHI lifecycle (id, scopes, parent, expiry, governance_source). ttl_seconds
    defaults to 24h.
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


def _resolve_c1z_path() -> str | None:
    """Return the .c1z path from CARRYALL_BATON_C1Z, else the bundled fixture, else None."""
    env_path = os.environ.get("CARRYALL_BATON_C1Z")
    if env_path and os.path.exists(env_path):
        return env_path
    try:
        from control_plane.c1z_fixtures import fixture_path

        return fixture_path()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("bundled c1z fixture unavailable: %s", exc)
        return None


def _baton_authorize(
    nhi: dict[str, Any], action: str, resource: str
) -> AuthorizeResult | None:
    """Attempt a real BatonBackend.check_access decision; None when unavailable.

    Returns None (caller falls back to synthetic) when the package, the .c1z, or
    a route for (action, resource) is missing, or on any backend fault.
    """
    route = _RESOURCE_ROUTES.get((action, resource))
    if route is None:
        return None
    uri, baton_action = route

    c1z_path = _resolve_c1z_path()
    if c1z_path is None:
        return None

    agent_id = nhi.get("agent_id", "unknown-agent")
    try:
        from carryall_baton import BatonBackend

        from control_plane.c1z_fixtures import PRINCIPAL_MAP

        principal_map = dict(PRINCIPAL_MAP)
        principal_map.setdefault(agent_id, agent_id)
        backend = BatonBackend(c1z_path, agent_to_principal=principal_map)
        envelope = _build_baton_envelope(agent_id, nhi.get("scopes"))
        result = backend.check_access(envelope, action=baton_action, uri=uri)
        allowed = result.decision == result.decision.ALLOW
        return AuthorizeResult(allowed, result.reason, _SOURCE_BATON)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "baton check_access fault for %s on %s/%s: %s (falling back to synthetic)",
            agent_id, action, resource, exc,
        )
        return None


def _build_baton_envelope(agent_id: str, scopes: list[str] | None) -> Any:
    """Build a signed authority_runtime envelope for the baton check_access call."""
    import authority_runtime

    valid_scopes = list(scopes) if scopes else ["nhi:placeholder"]
    priv_hex, _pub_hex = authority_runtime.generate_key_pair()
    return authority_runtime.create_simple_envelope(
        agent_id=agent_id, scopes=valid_scopes, private_key=priv_hex
    )


def _synthetic_authorize(
    nhi: dict[str, Any], action: str, resource: str
) -> AuthorizeResult:
    """Synthetic policy_check decision. Never raises; defaults allowed on error."""
    agent_id = nhi.get("agent_id", "unknown-agent")
    pseudo_vendor = f"{resource}:{action}"
    try:
        decision = policy_check.check_policy(
            vendor=pseudo_vendor, amount=0.0, requester=agent_id
        )
        return AuthorizeResult(decision.allowed, decision.reason, _SOURCE_SYNTHETIC)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "policy_check error for %s on %s/%s: %s (defaulting to allowed)",
            agent_id, action, resource, exc,
        )
        return AuthorizeResult(
            True, f"synthetic default: policy_check unavailable ({exc})", _SOURCE_SYNTHETIC
        )


def authorize(
    nhi: dict[str, Any],
    action: str,
    resource: str,
) -> AuthorizeResult:
    """Return an AuthorizeResult for the NHI performing action on resource.

    Routes through carryall_baton.BatonBackend.check_access against a real .c1z
    when the package, a .c1z, and a route for (action, resource) are present;
    otherwise falls back to the synthetic policy decision. Never raises. The C1
    SaaS is not on this path, so a missing C1 tenant is not a blocker.
    """
    baton_result = _baton_authorize(nhi, action, resource)
    if baton_result is not None:
        return baton_result
    return _synthetic_authorize(nhi, action, resource)


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
