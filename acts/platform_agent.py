"""acts/platform_agent.py -- Act 3 platform orchestrator for the STR agent.

Routes pricing and AEO-audit requests through their respective skills, logs
every earn event to the audit chain, and tracks platform-level metrics:
calls_served, revenue_earned_cents, properties_optimized.

C1 governance gates every call via c1_governance.issue_nhi + authorize.

Public API:
    serve_pricing_call(property_id, ...)  -> dict
    serve_aeo_call(listing_text, ...)     -> dict
    get_metrics()                         -> dict
    reset_metrics()                       -- testing only
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from control_plane.c1_governance import authorize, issue_nhi
from payments.mpp_server import (
    AEO_AUDIT_ENDPOINT_CENTS,
    PRICE_ENDPOINT_CENTS,
    _write_earn_event,
)
from skills.aeo_skill import AEOAuditRequest, AEOAuditResult, audit_listing
from skills.dynamic_pricing_skill import (
    PricingRecommendation,
    PricingRequest,
    recommend_price,
)

_PLATFORM_AGENT_ID: str = "str-platform-agent"
_PLATFORM_SCOPES: list[str] = ["str:price", "str:aeo-audit"]


# ---------------------------------------------------------------------------
# Platform metrics (module-level -- lightweight for demo; reset_metrics() for tests)
# ---------------------------------------------------------------------------

@dataclass
class _PlatformMetrics:
    """Mutable platform-level metrics accumulated across calls."""

    calls_served: int = 0
    revenue_earned_cents: int = 0
    properties_optimized: set = field(default_factory=set)


_metrics = _PlatformMetrics()


def reset_metrics() -> None:
    """Reset platform metrics. Use in tests only."""
    global _metrics
    _metrics = _PlatformMetrics()


def get_metrics() -> dict:
    """Return a snapshot of current platform metrics."""
    return {
        "calls_served": _metrics.calls_served,
        "revenue_earned_cents": _metrics.revenue_earned_cents,
        "revenue_earned_dollars": _metrics.revenue_earned_cents / 100,
        "properties_optimized": len(_metrics.properties_optimized),
        "property_ids": sorted(_metrics.properties_optimized),
    }


# ---------------------------------------------------------------------------
# C1 governance helper
# ---------------------------------------------------------------------------


def _authorize_platform(action: str) -> tuple[bool, str]:
    """Issue a fresh platform NHI and authorize the given action."""
    nhi = issue_nhi(_PLATFORM_AGENT_ID, _PLATFORM_SCOPES, ttl_seconds=3600)
    return authorize(nhi, action, resource="str-platform")


# ---------------------------------------------------------------------------
# Programmatic serve functions (for demo runner and tests)
# ---------------------------------------------------------------------------


def serve_pricing_call(
    property_id: str,
    current_rate: float,
    occupancy_rate: float,
    local_events: list[str] | None = None,
    comp_set_rates: list[float] | None = None,
    season: str = "shoulder",
    day_of_week: str = "sat",
    demo_token: str = "mpp_tok_demo",
    audit_path: str | None = None,
) -> dict:
    """Execute a pricing call through Act 3, log the earn event, update metrics.

    Returns a result dict with recommendation fields and earn event metadata.
    C1 governance gates the call via authorize(nhi, "price", "str-platform").
    #COMPLETION_DRIVE: demo_token default is valid in DEMO_MODE per mpp_server convention.
    """
    allowed, reason = _authorize_platform("price")
    if not allowed:
        return {"error": f"C1 governance denied: {reason}", "allowed": False}

    req = PricingRequest(
        property_id=property_id,
        current_rate=current_rate,
        occupancy_rate=occupancy_rate,
        local_events=local_events or [],
        comp_set_rates=comp_set_rates or [],
        season=season,
        day_of_week=day_of_week,
    )
    recommendation = recommend_price(req)

    earn_entry = _write_earn_event(
        service="price",
        amount_cents=PRICE_ENDPOINT_CENTS,
        token_id=demo_token,
        audit_path_env=audit_path,
    )

    _metrics.calls_served += 1
    _metrics.revenue_earned_cents += PRICE_ENDPOINT_CENTS
    _metrics.properties_optimized.add(property_id)

    return {
        "service": "price",
        "property_id": property_id,
        "amount_cents": PRICE_ENDPOINT_CENTS,
        "recommendation": {
            "recommended_rate": recommendation.recommended_rate,
            "confidence": recommendation.confidence,
            "reasoning": recommendation.reasoning,
            "suggested_title_tweak": recommendation.suggested_title_tweak,
            "valid_for_hours": recommendation.valid_for_hours,
        },
        "earn_event": {
            "chain_hash": earn_entry["chain_hash"],
            "seq": earn_entry["seq"],
            "timestamp": earn_entry["ts"],
        },
        "c1_authorized": True,
    }


def serve_aeo_call(
    listing_text: str,
    amenities_list: list[str] | None = None,
    existing_schema: dict | None = None,
    listing_url: str = "",
    demo_token: str = "mpp_tok_demo",
    audit_path: str | None = None,
) -> dict:
    """Execute an AEO audit call through Act 3, log the earn event, update metrics.

    Returns a result dict with audit fields and earn event metadata.
    C1 governance gates the call via authorize(nhi, "aeo-audit", "str-platform").
    """
    allowed, reason = _authorize_platform("aeo-audit")
    if not allowed:
        return {"error": f"C1 governance denied: {reason}", "allowed": False}

    req = AEOAuditRequest(
        listing_text=listing_text,
        amenities_list=amenities_list or [],
        existing_schema=existing_schema or {},
        listing_url=listing_url,
    )
    result = audit_listing(req)

    earn_entry = _write_earn_event(
        service="aeo-audit",
        amount_cents=AEO_AUDIT_ENDPOINT_CENTS,
        token_id=demo_token,
        audit_path_env=audit_path,
    )

    _metrics.calls_served += 1
    _metrics.revenue_earned_cents += AEO_AUDIT_ENDPOINT_CENTS

    return {
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
            "optimized_opening": result.optimized_opening,
            "reasoning_trace": result.reasoning_trace,
        },
        "earn_event": {
            "chain_hash": earn_entry["chain_hash"],
            "seq": earn_entry["seq"],
            "timestamp": earn_entry["ts"],
        },
        "c1_authorized": True,
    }
