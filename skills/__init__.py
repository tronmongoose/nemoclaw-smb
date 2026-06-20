"""skills: STR agent skill modules.

STRUCTURE NOTE: Act orchestrators live in acts/ (not agents/) to avoid colliding
with the existing agent/ package. Stripe primitives live in payments/ (not stripe/)
to avoid shadowing the stripe pip package.

Two skills available:
    skills.aeo_skill:             AEO scoring and listing optimization
    skills.dynamic_pricing_skill: Dynamic pricing recommendations via Nemotron Ultra
"""
from __future__ import annotations

from skills.aeo_skill import AEOAuditRequest, AEOAuditResult, audit_listing
from skills.dynamic_pricing_skill import (
    PricingRecommendation,
    PricingRequest,
    recommend_price,
)

__all__ = [
    "AEOAuditRequest",
    "AEOAuditResult",
    "audit_listing",
    "PricingRecommendation",
    "PricingRequest",
    "recommend_price",
]
