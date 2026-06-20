"""data/mock_ledger.py -- Deterministic synthetic STR ledger data.

Fixed-seed randomness ensures stable test output. prop-001 ("Sweet Clementine
by the Sea") intentionally carries a management fee anomaly: charged 0.22 vs
the contracted 0.20, which Act I's anomaly skill should detect.

Public API:
    PROPERTIES              -- property registry (dict keyed by property_id)
    MANAGEMENT_FEES_CHARGED -- actual fee pct per property
    MONTHLY_REVENUE         -- latest monthly revenue in cents per property
    CREW                    -- list of crew member dicts
    get_property(property_id)           -> dict
    get_ledger_summary(property_id, month) -> dict
    list_properties_for_owner(owner_id) -> list[str]
"""
from __future__ import annotations

PROPERTIES: dict[str, dict] = {
    "prop-001": {
        "name": "Sweet Clementine by the Sea",
        "airbnb_id": "838634728141757030",
        "owner_id": "owner-001",
        "management_contract_pct": 0.20,
        "city": "Oceanside",
        "state": "CA",
        "bedrooms": 3,
        "max_guests": 8,
    },
    "prop-002": {
        "name": "The Pelican Cottage",
        "airbnb_id": "112233445566778899",
        "owner_id": "owner-002",
        "management_contract_pct": 0.20,
        "city": "Oceanside",
        "state": "CA",
        "bedrooms": 2,
        "max_guests": 4,
    },
    "prop-003": {
        "name": "Harbor View Suite",
        "airbnb_id": "223344556677889900",
        "owner_id": "owner-002",
        "management_contract_pct": 0.18,
        "city": "San Diego",
        "state": "CA",
        "bedrooms": 1,
        "max_guests": 2,
    },
    "prop-004": {
        "name": "Sunset Ridge Cabin",
        "airbnb_id": "334455667788990011",
        "owner_id": "owner-003",
        "management_contract_pct": 0.20,
        "city": "Julian",
        "state": "CA",
        "bedrooms": 2,
        "max_guests": 6,
    },
    "prop-005": {
        "name": "Pacific Dunes Bungalow",
        "airbnb_id": "445566778899001122",
        "owner_id": "owner-003",
        "management_contract_pct": 0.20,
        "city": "Carlsbad",
        "state": "CA",
        "bedrooms": 2,
        "max_guests": 5,
    },
}

# prop-001 is charged 0.22 vs contract 0.20 -- the Act I anomaly to detect.
MANAGEMENT_FEES_CHARGED: dict[str, float] = {
    "prop-001": 0.22,
    "prop-002": 0.20,
    "prop-003": 0.18,
    "prop-004": 0.20,
    "prop-005": 0.20,
}

# Monthly revenue in cents. prop-001 = $4,200.
MONTHLY_REVENUE: dict[str, int] = {
    "prop-001": 420000,
    "prop-002": 310000,
    "prop-003": 195000,
    "prop-004": 280000,
    "prop-005": 255000,
}

CREW: list[dict] = [
    {"id": "crew-001", "name": "Maria S.", "role": "cleaner", "rate_cents": 8500},
    {"id": "crew-002", "name": "James T.", "role": "cleaner", "rate_cents": 8500},
    {"id": "crew-003", "name": "Falcon Maintenance", "role": "maintenance", "rate_cents": 15000},
]


def get_property(property_id: str) -> dict:
    """Return the property record for property_id.

    Raises KeyError when property_id is not found.
    """
    if property_id not in PROPERTIES:
        raise KeyError(f"Unknown property: {property_id!r}")
    return PROPERTIES[property_id]


def get_ledger_summary(property_id: str, month: str) -> dict:
    """Return a synthetic ledger summary dict for property_id and month (YYYY-MM).

    Includes revenue, contracted fee pct, charged fee pct, and fee delta in cents.
    """
    prop = get_property(property_id)
    revenue = MONTHLY_REVENUE.get(property_id, 0)
    contracted_pct = prop["management_contract_pct"]
    charged_pct = MANAGEMENT_FEES_CHARGED.get(property_id, contracted_pct)
    contracted_fee = int(revenue * contracted_pct)
    charged_fee = int(revenue * charged_pct)
    delta_cents = charged_fee - contracted_fee

    return {
        "property_id": property_id,
        "month": month,
        "revenue_cents": revenue,
        "contracted_fee_pct": contracted_pct,
        "charged_fee_pct": charged_pct,
        "contracted_fee_cents": contracted_fee,
        "charged_fee_cents": charged_fee,
        "fee_delta_cents": delta_cents,
        "anomaly": delta_cents != 0,
    }


def list_properties_for_owner(owner_id: str) -> list[str]:
    """Return list of property_ids belonging to owner_id."""
    return [pid for pid, p in PROPERTIES.items() if p["owner_id"] == owner_id]
