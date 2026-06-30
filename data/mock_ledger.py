"""data/mock_ledger.py: Deterministic synthetic STR ledger data.

Fixed-seed randomness ensures stable test output. prop-001 ("Sweet Clementine
by the Sea") intentionally carries a management fee anomaly: charged 0.22 vs
the contracted 0.20, which Act I's anomaly skill should detect.

Public API:
    PROPERTIES: property registry (dict keyed by property_id)
    MANAGEMENT_FEES_CHARGED: actual fee pct per property
    MONTHLY_REVENUE: latest monthly revenue in cents per property
    CREW: list of crew member dicts
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

# prop-001 is charged 0.22 vs contract 0.20: the Act I anomaly to detect.
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

# Trailing-month occupancy (0..1). prop-003 (Julian cabin) underperforms; prop-001
# (Sweet Clementine) overperforms. Drives the portfolio performance flagging.
PROPERTY_OCCUPANCY: dict[str, float] = {
    "prop-001": 0.82,
    "prop-002": 0.74,
    "prop-003": 0.41,
    "prop-004": 0.68,
    "prop-005": 0.59,
}

# Cleaner availability: the time each crew member is free from, vs _DEMO_NOW
# (2026-06-15T18:00Z). James (crew-002) is booked until 8pm; Maria (crew-001) is
# free, so a stalled clean assigned to James reassigns to Maria.
CREW_AVAILABILITY: dict[str, str] = {
    "crew-001": "2026-06-15T13:00:00+00:00",
    "crew-002": "2026-06-15T20:00:00+00:00",
}

# Turnover loop runs in this fixed order. Each stage hands off from the prior
# actor to the next: guest -> cleaner -> inspector -> booking platform.
TURNOVER_STAGES: tuple[str, ...] = ("checkout", "clean", "inspect", "ready")

# Role that owns each stage's handoff (used to label "from -> to" on a stall).
STAGE_ROLE: dict[str, str] = {
    "checkout": "guest",
    "clean": "cleaner",
    "inspect": "inspector",
    "ready": "booking platform",
}

# Per-property turnover state, seeded deterministically against _DEMO_NOW in
# acts/property_mgmt_agent.py. prop-001 (inspect) and prop-004 (clean) are
# intentionally stalled so the coordination agent has real handoffs to chase.
# Per-stage status is one of: done | in_progress | waiting | blocked.
PROPERTY_TURNOVER_STATE: dict[str, dict] = {
    "prop-001": {
        "checkout_date": "2026-06-15",
        "current_stage": "inspect",
        "stages": {
            "checkout": {"status": "done", "actor": "Guest party", "updated_ts": "2026-06-15T11:02:00+00:00"},
            "clean": {"status": "done", "actor": "Maria S.", "updated_ts": "2026-06-15T14:31:00+00:00"},
            "inspect": {"status": "blocked", "actor": "Inspector (unassigned)", "updated_ts": "2026-06-15T14:48:00+00:00",
                         "reason": "no inspector assigned 3h after cleaning finished"},
            "ready": {"status": "waiting", "actor": "Owner agent", "updated_ts": "2026-06-15T14:48:00+00:00"},
        },
    },
    "prop-002": {
        "checkout_date": "2026-06-14",
        "current_stage": "ready",
        "stages": {
            "checkout": {"status": "done", "actor": "Guest party", "updated_ts": "2026-06-14T10:40:00+00:00"},
            "clean": {"status": "done", "actor": "James T.", "updated_ts": "2026-06-14T13:10:00+00:00"},
            "inspect": {"status": "done", "actor": "Dana R.", "updated_ts": "2026-06-14T15:05:00+00:00"},
            "ready": {"status": "done", "actor": "Owner agent", "updated_ts": "2026-06-14T15:20:00+00:00"},
        },
    },
    "prop-003": {
        "checkout_date": "2026-06-15",
        "current_stage": "clean",
        "stages": {
            "checkout": {"status": "done", "actor": "Guest party", "updated_ts": "2026-06-15T10:55:00+00:00"},
            "clean": {"status": "in_progress", "actor": "Maria S.", "updated_ts": "2026-06-15T16:30:00+00:00"},
            "inspect": {"status": "waiting", "actor": "Dana R.", "updated_ts": "2026-06-15T16:30:00+00:00"},
            "ready": {"status": "waiting", "actor": "Owner agent", "updated_ts": "2026-06-15T16:30:00+00:00"},
        },
    },
    "prop-004": {
        "checkout_date": "2026-06-15",
        "current_stage": "clean",
        "stages": {
            "checkout": {"status": "done", "actor": "Guest party", "updated_ts": "2026-06-15T11:10:00+00:00"},
            "clean": {"status": "blocked", "actor": "James T.", "updated_ts": "2026-06-15T13:00:00+00:00",
                       "reason": "cleaner not started 5h after checkout"},
            "inspect": {"status": "waiting", "actor": "Dana R.", "updated_ts": "2026-06-15T13:00:00+00:00"},
            "ready": {"status": "waiting", "actor": "Owner agent", "updated_ts": "2026-06-15T13:00:00+00:00"},
        },
    },
    "prop-005": {
        "checkout_date": "2026-06-13",
        "current_stage": "ready",
        "stages": {
            "checkout": {"status": "done", "actor": "Guest party", "updated_ts": "2026-06-13T10:30:00+00:00"},
            "clean": {"status": "done", "actor": "Maria S.", "updated_ts": "2026-06-13T13:15:00+00:00"},
            "inspect": {"status": "done", "actor": "Dana R.", "updated_ts": "2026-06-13T15:00:00+00:00"},
            "ready": {"status": "done", "actor": "Owner agent", "updated_ts": "2026-06-13T15:10:00+00:00"},
        },
    },
}


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
