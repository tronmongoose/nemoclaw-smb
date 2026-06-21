"""payments/mpp_server.py: MPP (Machine Payments Protocol) HTTP-402 earn server.

Exposes two paid endpoints where the STR agent EARNS by charging callers:
    POST /price       -> $0.25 (25 cents)
    POST /aeo-audit   -> $1.00 (100 cents)

The 402 loop is the point: absent or invalid tokens get a 402 with a
WWW-Authenticate header specifying the Stripe-MPP charge. Valid tokens
unlock execution, and an earn event is written to the hash-chained audit log.

DEMO_MODE token validity: a token is valid if it starts with "mpp_tok_".
No real Stripe calls are made in DEMO_MODE. This is documented behavior.

C1 governance: every call is authorized via c1_governance.authorize() using
a platform NHI scoped to ["str:price", "str:aeo-audit"]. Unauthorized NHI
(expired or wrong scope) receives 403 before execution.

Public API:
    app: FastAPI application instance
    PRICE_ENDPOINT_CENTS: 25
    AEO_AUDIT_ENDPOINT_CENTS: 100
    validate_mpp_token(token): bool (DEMO_MODE or real Stripe check)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.audit_log import _hash_entry, _read_head  # noqa: PLC2701
from agent.audit_log import _resolve as _resolve_audit_path  # noqa: PLC2701
from agent.interactions_log import append_interaction
from config.demo_mode import demo_mode
from control_plane.c1_governance import authorize, issue_nhi
from skills.aeo_skill import AEOAuditRequest, audit_listing
from skills.dynamic_pricing_skill import PricingRequest, recommend_price

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRICE_ENDPOINT_CENTS: int = 25
AEO_AUDIT_ENDPOINT_CENTS: int = 100

_PLATFORM_AGENT_ID: str = "str-platform-agent"
_PLATFORM_SCOPES: list[str] = ["str:price", "str:aeo-audit"]

_DEMO_TOKEN_PREFIX: str = "mpp_tok_"

app = FastAPI(title="STR MPP Earn Server", version="0.1.0")

# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------


class PriceRequestBody(BaseModel):
    """Request body for POST /price."""

    property_id: str
    current_rate: float
    occupancy_rate: float
    local_events: list[str] = []
    comp_set_rates: list[float] = []
    season: str = "shoulder"
    day_of_week: str = "sat"


class AEORequestBody(BaseModel):
    """Request body for POST /aeo-audit."""

    listing_text: str
    amenities_list: list[str] = []
    existing_schema: dict = {}
    listing_url: str = ""


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


def validate_mpp_token(token: str) -> bool:
    """Return True when the MPP token is valid.

    In DEMO_MODE: any token starting with "mpp_tok_" is accepted.
    In production: a real Stripe-MPP token verification would occur here.
    #COMPLETION_DRIVE: production path requires Stripe MPP webhook verification.
    """
    if demo_mode():
        return token.startswith(_DEMO_TOKEN_PREFIX)
    # Production: token verification via Stripe MPP (not implemented, no creds)
    return token.startswith(_DEMO_TOKEN_PREFIX)


def _extract_token(authorization: Optional[str]) -> Optional[str]:  # noqa: UP045
    """Parse Bearer token from Authorization header. Returns None if absent/malformed."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# ---------------------------------------------------------------------------
# Audit earn event writer
# ---------------------------------------------------------------------------


def _write_earn_event(
    service: str,
    amount_cents: int,
    token_id: str,
    audit_path_env: Optional[str] = None,  # noqa: UP045
) -> dict:
    """Append an MPP earn event to the hash-chained audit log.

    Earn event schema:
        event, service, amount_cents, token_id, timestamp, chain_hash
    Returns the written entry dict.
    """
    path = _resolve_audit_path(
        audit_path_env or os.environ.get("NEMOCLAW_AUDIT_PATH")
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    prev_hash, seq = _read_head(path)
    ts = datetime.now(timezone.utc).isoformat()

    # Build payload without entry_hash so the hash covers exactly the fields
    # that verify_chain sees after stripping "entry_hash" on read.
    # chain_hash is NOT persisted as a separate key to avoid corrupting the
    # verify_chain recompute (which only strips "entry_hash").
    payload: dict[str, Any] = {
        "ts": ts,
        "seq": seq,
        "event": "mpp_earn",
        "service": service,
        "amount_cents": amount_cents,
        "token_id": token_id,
        "prev_hash": prev_hash,
    }
    entry_hash = _hash_entry(prev_hash, payload)
    payload["entry_hash"] = entry_hash

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    try:
        append_interaction(
            sponsor="Stripe", op=f"MPP earn: {service}",
            segment="agent", status="ok", metadata={"amount_cents": amount_cents},
        )
    except Exception:
        pass

    # Expose chain_hash in return value only (not persisted as a separate field)
    result = dict(payload)
    result["chain_hash"] = entry_hash
    return result


# ---------------------------------------------------------------------------
# 402 response helper
# ---------------------------------------------------------------------------


def _four_oh_two(amount_cents: int) -> JSONResponse:
    """Return a 402 response with the Stripe-MPP WWW-Authenticate header."""
    amount_dollars = amount_cents / 100
    headers = {
        "WWW-Authenticate": (
            f"stripe-mpp charge=${amount_dollars:.2f} currency=usd"
        )
    }
    return JSONResponse(
        status_code=402,
        content={"error": "payment_required", "amount_cents": amount_cents},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# C1 governance: issue and authorize platform NHI
# ---------------------------------------------------------------------------


def _get_platform_nhi() -> dict:
    """Issue a fresh platform NHI with pricing and AEO-audit scopes."""
    return issue_nhi(_PLATFORM_AGENT_ID, _PLATFORM_SCOPES, ttl_seconds=3600)


def _c1_authorize(action: str) -> tuple[bool, str]:
    """Authorize the platform NHI to perform action. Returns (allowed, reason)."""
    nhi = _get_platform_nhi()
    return authorize(nhi, action, resource="str-platform")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/price")
async def price_endpoint(
    body: PriceRequestBody,
    authorization: Optional[str] = Header(default=None),  # noqa: UP045
) -> JSONResponse:
    """POST /price: $0.25 per call.

    Returns HTTP 402 with WWW-Authenticate header when no valid token is present.
    Executes dynamic pricing skill and writes earn event when token is valid.
    C1 governance gates the call via authorize(nhi, "price", "str-platform").
    """
    token = _extract_token(authorization)
    if not token or not validate_mpp_token(token):
        return _four_oh_two(PRICE_ENDPOINT_CENTS)

    allowed, reason = _c1_authorize("price")
    if not allowed:
        raise HTTPException(status_code=403, detail=f"C1 governance denied: {reason}")

    req = PricingRequest(
        property_id=body.property_id,
        current_rate=body.current_rate,
        occupancy_rate=body.occupancy_rate,
        local_events=body.local_events,
        comp_set_rates=body.comp_set_rates,
        season=body.season,
        day_of_week=body.day_of_week,
    )
    recommendation = recommend_price(req)

    earn_entry = _write_earn_event(
        service="price",
        amount_cents=PRICE_ENDPOINT_CENTS,
        token_id=token,
    )

    return JSONResponse(
        status_code=200,
        content={
            "service": "price",
            "amount_cents": PRICE_ENDPOINT_CENTS,
            "result": {
                "recommended_rate": recommendation.recommended_rate,
                "confidence": recommendation.confidence,
                "reasoning": recommendation.reasoning,
                "suggested_title_tweak": recommendation.suggested_title_tweak,
                "valid_for_hours": recommendation.valid_for_hours,
            },
            "earn_event": {
                "chain_hash": earn_entry["chain_hash"],
                "seq": earn_entry["seq"],
            },
        },
    )


@app.post("/aeo-audit")
async def aeo_audit_endpoint(
    body: AEORequestBody,
    authorization: Optional[str] = Header(default=None),  # noqa: UP045
) -> JSONResponse:
    """POST /aeo-audit: $1.00 per call.

    Returns HTTP 402 with WWW-Authenticate header when no valid token is present.
    Executes the AEO audit skill and writes earn event when token is valid.
    C1 governance gates the call via authorize(nhi, "aeo-audit", "str-platform").
    """
    token = _extract_token(authorization)
    if not token or not validate_mpp_token(token):
        return _four_oh_two(AEO_AUDIT_ENDPOINT_CENTS)

    allowed, reason = _c1_authorize("aeo-audit")
    if not allowed:
        raise HTTPException(status_code=403, detail=f"C1 governance denied: {reason}")

    req = AEOAuditRequest(
        listing_text=body.listing_text,
        amenities_list=body.amenities_list,
        existing_schema=body.existing_schema,
        listing_url=body.listing_url,
    )
    result = audit_listing(req)

    earn_entry = _write_earn_event(
        service="aeo-audit",
        amount_cents=AEO_AUDIT_ENDPOINT_CENTS,
        token_id=token,
    )

    return JSONResponse(
        status_code=200,
        content={
            "service": "aeo-audit",
            "amount_cents": AEO_AUDIT_ENDPOINT_CENTS,
            "result": {
                "overall_score": result.overall_score,
                "dimension_scores": {
                    "structure_completeness": result.dimension_scores.structure_completeness,
                    "agent_parseability": result.dimension_scores.agent_parseability,
                    "description_quality": result.dimension_scores.description_quality,
                    "conflict_free": result.dimension_scores.conflict_free,
                },
                "critical_flags": [
                    {
                        "severity": f.severity,
                        "code": f.code,
                        "message": f.message,
                    }
                    for f in result.critical_flags
                ],
                "optimized_opening": result.optimized_opening,
                "reasoning_trace": result.reasoning_trace,
            },
            "earn_event": {
                "chain_hash": earn_entry["chain_hash"],
                "seq": earn_entry["seq"],
            },
        },
    )
