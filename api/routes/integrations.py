"""Integration status and per-pillar verification routes for NemoClaw SMB.

Exports (via router):
    GET /integrations/status: fast, no network; returns agent node + 4 pillar nodes
    GET /integrations/verify: real probe for a named pillar id; returns id/status/detail/latency_ms
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from agent.hermes_client import hermes_available
from agent.nvidia_client import nemotron_available

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _carryall_baton_importable() -> bool:
    """Return True when carryall_baton can be imported at runtime."""
    try:
        import carryall_baton  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _build_agent_node() -> dict[str, Any]:
    """Build the core agent node. No network calls."""
    return {
        "id": "agent",
        "label": "NemoClaw Agent",
        "kind": "core",
        "status": "REAL",
        "detail": "guardrail -> approval -> execute -> SHA-256 hash-chained audit",
        "source": "local",
    }


def _build_nemotron_node() -> dict[str, Any]:
    """Build the Nemotron pillar node based on key presence only."""
    keyed = nemotron_available()
    status = "LIVE-CAPABLE" if keyed else "NOT-CONFIGURED"
    detail = "NVIDIA_NIM_API_KEY present" if keyed else "NVIDIA_NIM_API_KEY not set"
    return {
        "id": "nemotron",
        "label": "NVIDIA Nemotron",
        "vendor": "NVIDIA",
        "kind": "reasoning",
        "status": status,
        "detail": detail,
        "skills": ["anomaly reasoning", "dynamic pricing", "AEO scoring"],
    }


def _build_hermes_node() -> dict[str, Any]:
    """Build the Hermes pillar node based on key presence only."""
    keyed = hermes_available()
    status = "LIVE-CAPABLE" if keyed else "NOT-CONFIGURED"
    detail = "NOUS_PORTAL_API_KEY present" if keyed else "NOUS_PORTAL_API_KEY not set"
    return {
        "id": "hermes",
        "label": "Nous Hermes",
        "vendor": "Nous Research",
        "kind": "orchestration",
        "status": status,
        "detail": detail,
        "skills": ["intent parsing", "skill orchestration"],
    }


def _build_stripe_node() -> dict[str, Any]:
    """Build the Stripe pillar node. Always DEMO in NemoClaw (test-mode, mocked)."""
    return {
        "id": "stripe",
        "label": "Stripe",
        "vendor": "Stripe",
        "kind": "payments",
        "status": "DEMO",
        "detail": "test-mode, mocked; no funds move",
        "skills": [
            "Issuing for Agents",
            "Connect",
            "Global Payouts",
            "Metronome UBP",
            "MPP / HTTP-402",
        ],
    }


def _build_conductorone_node() -> dict[str, Any]:
    """Build the ConductorOne pillar node. REAL when carryall_baton importable, else DEMO."""
    if _carryall_baton_importable():
        status = "REAL"
        detail = "Baton grant-matching via carryall-baton-backend against a .c1z"
    else:
        status = "DEMO"
        detail = "carryall_baton not installed; synthetic policy decisions active"
    return {
        "id": "conductorone",
        "label": "C1",
        "vendor": "C1",
        "kind": "governance",
        "status": status,
        "detail": detail,
        "skills": ["scoped NHIs", "Baton entitlements", "authorize"],
    }


@router.get("/status")
def get_status() -> dict[str, Any]:
    """Return the agent node and all four pillar nodes. No network calls."""
    return {
        "agent": _build_agent_node(),
        "pillars": [
            _build_nemotron_node(),
            _build_hermes_node(),
            _build_stripe_node(),
            _build_conductorone_node(),
        ],
    }


def _map_probe_status(probe_status: str) -> str:
    """Map a reality_report probe status string to the contract status vocabulary.

    MOCK and HOLLOW collapse to DEMO. LIVE-OK and LIVE-FAIL pass through.
    Everything else is preserved.
    """
    if probe_status in ("MOCK", "HOLLOW"):
        return "DEMO"
    return probe_status


def _verify_nemotron() -> dict[str, Any]:
    """Run the Nemotron probe and return a contract-shaped result."""
    from verification.reality_report import probe_nemotron

    result = probe_nemotron()
    status = _map_probe_status(result.status)
    return {"id": "nemotron", "status": status, "detail": result.detail}


def _verify_hermes() -> dict[str, Any]:
    """Run the Hermes probe and return a contract-shaped result."""
    from verification.reality_report import probe_hermes

    result = probe_hermes()
    status = _map_probe_status(result.status)
    return {"id": "hermes", "status": status, "detail": result.detail}


def _verify_stripe() -> dict[str, Any]:
    """Run the Stripe SDK probe and return a contract-shaped result. Always DEMO here."""
    from verification.reality_report import probe_stripe_sdk

    result = probe_stripe_sdk()
    status = _map_probe_status(result.status)
    # Stripe in NemoClaw is test-only; collapse LIVE-OK to DEMO for the contract
    if status == "LIVE-OK":
        status = "DEMO"
    return {"id": "stripe", "status": status, "detail": result.detail}


def _verify_conductorone() -> dict[str, Any]:
    """Run a real authorize() call and return a contract-shaped result.

    Issues a synthetic NHI then calls authorize on (price, str-platform). Surfaces
    the baton-carryall source when the backend is live.
    """
    try:
        from control_plane.c1_governance import authorize, issue_nhi

        nhi = issue_nhi("nemoclaw-verify-probe", ["price:str-platform"])
        result = authorize(nhi, "price", "str-platform")
        source = getattr(result, "source", "unknown")
        allowed = result.allowed if hasattr(result, "allowed") else result[0]
        reason = result.reason if hasattr(result, "reason") else result[1]
        if source == "baton-carryall":
            status = "REAL"
            detail = f"baton-carryall; allowed={allowed}; {reason[:80]}"
        else:
            status = "LIVE-OK"
            detail = f"source={source}; allowed={allowed}; {reason[:80]}"
        return {"id": "conductorone", "status": status, "detail": detail}
    except Exception as exc:  # noqa: BLE001
        return {
            "id": "conductorone",
            "status": "LIVE-FAIL",
            "detail": str(exc)[:120],
        }


_PILLAR_VERIFIERS = {
    "nemotron": _verify_nemotron,
    "hermes": _verify_hermes,
    "stripe": _verify_stripe,
    "conductorone": _verify_conductorone,
}


@router.get("/verify")
def verify_pillar(pillar: str) -> dict[str, Any]:
    """Run a real probe for the named pillar and return id/status/detail/latency_ms.

    pillar must be one of: nemotron, hermes, stripe, conductorone.
    Returns 400 for unknown pillar ids. Never raises on probe failure; returns
    LIVE-FAIL with the error in detail instead.
    """
    verifier = _PILLAR_VERIFIERS.get(pillar)
    if verifier is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown pillar '{pillar}'. Valid: {sorted(_PILLAR_VERIFIERS)}",
        )

    t0 = time.perf_counter()
    try:
        outcome = verifier()
    except Exception as exc:  # noqa: BLE001
        outcome = {
            "id": pillar,
            "status": "LIVE-FAIL",
            "detail": str(exc)[:120],
        }
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    outcome["latency_ms"] = latency_ms
    return outcome
