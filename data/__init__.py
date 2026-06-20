"""data -- STR mock data package.

STRUCTURE NOTE: act orchestrators live in acts/ (not agents/) to avoid colliding
with the existing agent/ package. Stripe primitives live in payments/ (not stripe/)
to avoid shadowing the stripe pip package.

Exports (re-exported for convenience):
    PROPERTIES              -- property registry dict keyed by property_id
    MANAGEMENT_FEES_CHARGED -- actual fee pct per property (prop-001 is the anomaly)
    MONTHLY_REVENUE         -- latest monthly revenue per property in cents
    CREW                    -- list of crew member dicts
    get_property            -- look up a property by id
    get_ledger_summary      -- summary dict for a property/month
    list_properties_for_owner -- property ids for a given owner
    LISTINGS                -- dict of listing data keyed by listing_id
    CLEMENTINE_AEO          -- pre-seeded AEO result for Sweet Clementine
    PELICAN_AEO             -- pre-seeded AEO result for The Pelican Cottage
"""
from __future__ import annotations

from data.mock_ledger import (
    CREW,
    MANAGEMENT_FEES_CHARGED,
    MONTHLY_REVENUE,
    PROPERTIES,
    get_ledger_summary,
    get_property,
    list_properties_for_owner,
)
from data.mock_listings import CLEMENTINE_AEO, LISTINGS, PELICAN_AEO

__all__ = [
    "PROPERTIES",
    "MANAGEMENT_FEES_CHARGED",
    "MONTHLY_REVENUE",
    "CREW",
    "get_property",
    "get_ledger_summary",
    "list_properties_for_owner",
    "LISTINGS",
    "CLEMENTINE_AEO",
    "PELICAN_AEO",
]
