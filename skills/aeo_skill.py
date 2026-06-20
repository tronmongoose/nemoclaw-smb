"""skills/aeo_skill.py -- Agent Engine Optimization (AEO) audit skill.

Scores STR listings for machine parseability by AI booking agents.
Sweet Clementine result is pre-seeded (instant demo, no inference required).
All other listings run the deterministic rubric defined below.

Public API:
    AEOAuditRequest   -- input dataclass
    AEOAuditResult    -- output dataclass
    DimensionScores   -- 4 x 25 pts breakdown
    AEOFlag           -- severity-coded issue with plain_english explanation
    audit_listing(req) -> AEOAuditResult
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from data.mock_listings import CLEMENTINE_AEO, LISTINGS
from config.model_routing import route_for  # noqa: F401 (wires routing table check)

# ---------------------------------------------------------------------------
# The 10 standard booking questions an AI agent must answer from STRUCTURED data.
# Each is worth 2.5 pts in Dimension 2 (Agent Parseability).
# ---------------------------------------------------------------------------
BOOKING_QUESTIONS: List[str] = [
    "can_bring_dog",
    "checkin_time",
    "checkout_time",
    "parking_available",
    "smoking_policy",
    "cancellation_policy",
    "minimum_stay",
    "max_guests",
    "outdoor_space",
    "wifi_included",
]

POINTS_PER_QUESTION: float = 2.5

# Fields checked for Dimension 1 (Structure Completeness), each worth ~2.27 pts
STRUCTURE_FIELDS: List[str] = [
    "checkin_time", "checkout_time", "max_guests", "pet_allowed",
    "pet_species", "pet_fee", "smoking_policy", "cancellation_tier",
    "min_stay", "parking_available", "parking_type", "quiet_hours",
    "permit_number",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AEOFlag:
    """A scored issue found during the AEO audit."""

    severity: str          # CRITICAL | HIGH | MEDIUM | LOW
    code: str              # machine-readable code
    message: str           # technical description
    plain_english: str     # what a real guest would experience


@dataclass
class DimensionScores:
    """Four scoring dimensions, 25 pts each, summing to 100."""

    structure_completeness: int   # Dim 1: metadata fields present and structured
    agent_parseability: int       # Dim 2: 10 booking questions answerable
    description_quality: int      # Dim 3: AI-summarization quality
    conflict_free: int            # Dim 4: no structured/prose contradictions


@dataclass
class AEOAuditRequest:
    """Input to the AEO audit skill."""

    listing_text: str             # Full prose description
    amenities_list: List[str]     # Structured amenities already present
    existing_schema: dict         # Any existing JSON-LD/schema.org data (may be empty)
    listing_url: str              # For reference only -- not fetched at runtime


@dataclass
class AEOAuditResult:
    """Full AEO audit output."""

    overall_score: int
    dimension_scores: DimensionScores
    critical_flags: List[AEOFlag]
    optimized_opening: str
    json_ld_schema: dict
    reasoning_trace: str


# ---------------------------------------------------------------------------
# Pre-seeded Sweet Clementine result (instant demo, no live inference needed).
# Canonical per master brief: 51/100 with sub-scores 14/11/16/10.
# COMPLETION_DRIVE: this result is intentionally hardcoded per brief's instructions
#   so the demo is reproducible without API credentials.
# ---------------------------------------------------------------------------

_CLEMENTINE_JSON_LD: dict = {
    "@context": "https://schema.org",
    "@type": "LodgingBusiness",
    "name": "Sweet Clementine by the Sea",
    "description": (
        "2BR/1BA beach cottage in Oceanside CA. 6 guests max. "
        "10-min walk to Strand Beach."
    ),
    "address": {
        "@type": "PostalAddress",
        "addressLocality": "Oceanside",
        "addressRegion": "CA",
        "addressCountry": "US",
    },
    "numberOfRooms": 2,
    "amenityFeature": [
        {"@type": "LocationFeatureSpecification", "name": "WiFi", "value": True},
        {"@type": "LocationFeatureSpecification", "name": "Kitchen", "value": True},
        {"@type": "LocationFeatureSpecification", "name": "Washer/Dryer", "value": True},
        {"@type": "LocationFeatureSpecification", "name": "Fire Pit", "value": True},
        {"@type": "LocationFeatureSpecification", "name": "Fenced Backyard", "value": True},
        {"@type": "LocationFeatureSpecification", "name": "Smart TV", "value": True},
        {"@type": "LocationFeatureSpecification", "name": "Parking", "value": True},
    ],
    "checkinTime": "16:00",
    "checkoutTime": "11:00",
    "petsAllowed": True,
    "smokingAllowed": False,
    "x-str-permit": "018234",
    "x-str-pet-policy": {
        "allowed": True,
        "species": ["dogs"],
        "maxCount": 2,
        "feePerPetPerNight": 30,
        "currency": "USD",
    },
    "x-str-cancellation-policy": {
        "tier": "strict",
        "fullRefundDaysBeforeArrival": 30,
        "noRefundWithin": 30,
        "earlyDepartureRefund": False,
    },
    "x-str-parking": {
        "available": True,
        "type": ["garage", "street"],
        "garageWidthFt": 6,
        "garageDepthFt": 8,
        "smallCarOnly": True,
        "notes": "Only small cars fit in garage. Street parking available.",
    },
    "x-str-quiet-hours": {"start": "21:00", "end": "09:00"},
    "x-str-max-occupancy": 6,
    "x-str-active-construction-nearby": True,
    "x-str-cameras": {
        "exterior": True,
        "locations": ["garage door", "front porch"],
        "recording": "24/7",
    },
}

_CLEMENTINE_FLAGS: List[AEOFlag] = [
    AEOFlag(
        severity="CRITICAL",
        code="pet_species_conflict",
        message=(
            "Listing intro reads 'pet-friendly home' with no species restriction. "
            "House rules read 'We only accept dogs.' "
            "Structured pet field shows petsAllowed=true with no species qualifier."
        ),
        plain_english=(
            "A cat owner reading the listing intro would believe cats are welcome. "
            "They would be turned away at the door. This conflict causes AI booking "
            "agents to misrepresent the pet policy to every traveler who asks."
        ),
    ),
    AEOFlag(
        severity="CRITICAL",
        code="checkin_time_missing",
        message="Check-in time is not stated anywhere in the listing -- structured or prose.",
        plain_english=(
            "AI booking agents cannot answer 'What time is check-in?' "
            "for this property. Every guest inquiry requires a host response."
        ),
    ),
    AEOFlag(
        severity="CRITICAL",
        code="checkout_time_missing",
        message="Checkout time is not stated anywhere in the listing -- structured or prose.",
        plain_english=(
            "AI booking agents cannot answer 'What time is checkout?' "
            "for this property. Late checkout requests cannot be auto-processed."
        ),
    ),
    AEOFlag(
        severity="HIGH",
        code="min_stay_missing",
        message="Minimum stay is not stated. Pricing queries for single-night stays will be incomplete.",
        plain_english=(
            "Travelers asking an AI agent about availability may see this property "
            "surface for stays shorter than the host actually accepts."
        ),
    ),
    AEOFlag(
        severity="HIGH",
        code="cancellation_prose_only",
        message="Cancellation policy is prose-only. No machine-readable tier is set.",
        plain_english=(
            "AI agents must read and parse unstructured text to determine refund "
            "eligibility. A wrong parse means a guest gets incorrect cancellation terms."
        ),
    ),
    AEOFlag(
        severity="MEDIUM",
        code="construction_not_structured",
        message="Active construction disclosure is buried in description, not a structured field.",
        plain_english=(
            "Guests who ask 'is there any construction nearby?' will not receive "
            "a reliable answer from an AI booking agent."
        ),
    ),
    AEOFlag(
        severity="LOW",
        code="fire_pit_wood_unstructured",
        message="Fire pit wood availability is mentioned in amenities text but not as a structured attribute.",
        plain_english="Guests may arrive expecting wood provided and find they must source it themselves.",
    ),
]

_CLEMENTINE_OPENING: str = (
    "2BR/1BA beach cottage, Oceanside CA. 6 guests max. 10-min walk to Strand Beach. "
    "Pet-friendly (dogs only, max 2, $30/night/pet). Private fenced backyard with fire pit. "
    "Quiet hours 9pm-9am. No smoking (entire property). 30-day cancellation policy. "
    "STR Permit 018234. Note: minor construction two doors down."
)

_CLEMENTINE_REASONING: str = (
    "Score 51/100. Structure completeness (14/25): check-in time, checkout time, "
    "minimum stay, and pet fee as a discrete structured field are all absent. "
    "Agent parseability (11/25): 3 of 10 booking questions fully answerable from "
    "structured data; partial prose answers score 0 in machine context. "
    "Description quality (16/25): listing opens with 'Hey Future Guests' wasting "
    "150 characters; superlative filler and emotional language degrade AI summarization. "
    "Conflict-free (10/25): CRITICAL dog-only restriction appears only in house rules, "
    "contradicting an unrestricted 'pet-friendly' claim in the intro."
)

_SWEET_CLEMENTINE_RESULT = AEOAuditResult(
    overall_score=CLEMENTINE_AEO["overall_score"],
    dimension_scores=DimensionScores(
        structure_completeness=14,
        agent_parseability=11,
        description_quality=16,
        conflict_free=10,
    ),
    critical_flags=_CLEMENTINE_FLAGS,
    optimized_opening=_CLEMENTINE_OPENING,
    json_ld_schema=_CLEMENTINE_JSON_LD,
    reasoning_trace=_CLEMENTINE_REASONING,
)


# ---------------------------------------------------------------------------
# Live rubric helpers -- used for all listings that are NOT Sweet Clementine.
# ---------------------------------------------------------------------------

def _score_structure(req: AEOAuditRequest) -> int:
    """Dimension 1: Structure completeness. 25 pts across 11 policy fields.

    Each present/structured field earns proportional credit.
    Points deducted for any field that exists only in prose or is absent entirely.
    """
    schema = req.existing_schema
    text = req.listing_text.lower()
    amenities = [a.lower() for a in req.amenities_list]

    pts = 0
    # Check-in and checkout times -- 5 pts each, only if structured
    if schema.get("checkinTime"):
        pts += 5
    if schema.get("checkoutTime"):
        pts += 5
    # Max occupancy -- 3 pts
    occ = schema.get("x-str-max-occupancy") or schema.get("occupancy", {})
    if occ:
        pts += 3
    # Pet policy with species and fee -- 4 pts total
    pet = schema.get("x-str-pet-policy", {})
    if pet.get("allowed") is not None:
        pts += 1
    if pet.get("species"):
        pts += 2
    if pet.get("feePerPetPerNight") is not None:
        pts += 1
    # Smoking policy -- 2 pts if structured
    if "smokingAllowed" in schema:
        pts += 2
    # Cancellation tier -- 2 pts if structured
    cancel = schema.get("x-str-cancellation-policy", {})
    if cancel.get("tier"):
        pts += 2
    # Parking -- 2 pts if structured with type
    parking = schema.get("x-str-parking", {})
    if parking.get("available") is not None:
        pts += 1
    if parking.get("type"):
        pts += 1
    # Quiet hours -- 1 pt
    if schema.get("x-str-quiet-hours"):
        pts += 1
    # Permit number -- 2 pts
    if schema.get("x-str-permit") or "permit" in text:
        pts += 2
    # Min stay -- 2 pts if structured
    if schema.get("x-str-min-stay") or "minimum stay" in text:
        pts += 1

    return min(pts, 25)


def _score_parseability(req: AEOAuditRequest) -> int:
    """Dimension 2: Agent parseability. 2.5 pts per booking question, structured only.

    Partial or prose-only answers score 0; only structured fields count.
    #COMPLETION_DRIVE: prose detection is conservative; structured schema is the gate.
    """
    schema = req.existing_schema
    amenities = [a.lower() for a in req.amenities_list]

    answered = 0.0
    pet = schema.get("x-str-pet-policy", {})
    parking = schema.get("x-str-parking", {})

    # 1. can_bring_dog -- need structured pet policy with species
    if pet.get("species"):
        answered += 1
    # 2. checkin_time
    if schema.get("checkinTime"):
        answered += 1
    # 3. checkout_time
    if schema.get("checkoutTime"):
        answered += 1
    # 4. parking_available
    if parking.get("available") is not None:
        answered += 1
    # 5. smoking_policy
    if "smokingAllowed" in schema:
        answered += 1
    # 6. cancellation_policy
    if schema.get("x-str-cancellation-policy", {}).get("tier"):
        answered += 1
    # 7. minimum_stay
    if schema.get("x-str-min-stay"):
        answered += 1
    # 8. max_guests
    if schema.get("x-str-max-occupancy"):
        answered += 1
    # 9. outdoor_space -- WiFi in amenities list counts as structured
    outdoor_terms = {"fire pit", "backyard", "patio", "deck", "balcony", "outdoor"}
    if any(t in a for a in amenities for t in outdoor_terms):
        answered += 1
    # 10. wifi_included
    if "wifi" in amenities or "wi-fi" in amenities:
        answered += 1

    return min(int(answered * POINTS_PER_QUESTION), 25)


def _score_description(req: AEOAuditRequest) -> int:
    """Dimension 3: Description quality for AI summarization. Up to 25 pts.

    Front-loaded facts (+5), no superlatives (+5), explicit cancellation (+5),
    no internal contradictions with structured fields (+10).
    """
    text = req.listing_text
    schema = req.existing_schema
    pts = 25  # start full, deduct

    superlatives = [
        "best", "amazing", "wonderful", "perfect", "ultimate",
        "incredible", "unbeatable", "gorgeous", "breathtaking", "luxurious",
    ]
    # Front-loaded facts: first 150 chars should contain BR/BA or guest count
    opening = text[:150].lower()
    has_facts = any(k in opening for k in ["br", "ba", "bedroom", "bathroom", "guests", "max"])
    if not has_facts:
        pts -= 5

    # Superlatives deduct up to 5 pts
    if any(s in text.lower() for s in superlatives):
        pts -= 5

    # Explicit cancellation in description
    if "cancellation" not in text.lower():
        pts -= 5

    # No internal contradictions with schema (pets/smoking/capacity)
    pet = schema.get("x-str-pet-policy", {})
    if pet.get("allowed") is True and "no pets" in text.lower():
        pts -= 10
    if pet.get("allowed") is False and "pet" in text.lower() and "no pet" not in text.lower():
        pts -= 5

    return max(pts, 0)


def _score_conflict_free(req: AEOAuditRequest) -> int:
    """Dimension 4: Conflict-free. Starts at 25 -- deductions for contradictions.

    -25 for a structured/prose contradiction on a material policy field.
    -10 for a credibility mismatch (claim vs. stated data).
    -5 for duplicate or inconsistent field presentation.
    """
    schema = req.existing_schema
    text = req.listing_text.lower()
    amenities = [a.lower() for a in req.amenities_list]
    pts = 25

    # Material policy contradiction: pets structured vs prose
    pet = schema.get("x-str-pet-policy", {})
    schema_pets_ok = pet.get("allowed") is True
    schema_no_pets = pet.get("allowed") is False or schema.get("petsAllowed") is False
    prose_pets_ok = "pet" in text and "no pet" not in text and "not allowed" not in text
    prose_no_pets = "no pet" in text or "no dogs" in text or "no cats" in text

    if schema_pets_ok and prose_no_pets:
        pts -= 25
    elif schema_no_pets and prose_pets_ok:
        pts -= 25

    # Smoking contradiction
    if schema.get("smokingAllowed") is True and "no smoking" in text:
        pts -= 25
    elif schema.get("smokingAllowed") is False and "smoking allowed" in text:
        pts -= 25

    # Credibility mismatch: superlative claim with no supporting data
    if "5 star" in text and schema.get("x-str-review-value-score", 5.0) < 4.5:
        pts -= 10

    # Duplicate/inconsistent field: pet fee mentioned multiple times with different values
    pet_fee_mentions = text.count("pet fee") + text.count("pet charge")
    if pet_fee_mentions > 1:
        pts -= 5

    return max(pts, 0)


def _build_flags(req: AEOAuditRequest, scores: DimensionScores) -> List[AEOFlag]:
    """Build the AEOFlag list from scoring observations."""
    schema = req.existing_schema
    text = req.listing_text.lower()
    flags: List[AEOFlag] = []

    if not schema.get("checkinTime"):
        flags.append(AEOFlag(
            severity="CRITICAL",
            code="checkin_time_missing",
            message="Check-in time is absent from structured schema.",
            plain_english="AI booking agents cannot answer 'What time is check-in?' without calling the host.",
        ))
    if not schema.get("checkoutTime"):
        flags.append(AEOFlag(
            severity="CRITICAL",
            code="checkout_time_missing",
            message="Checkout time is absent from structured schema.",
            plain_english="AI booking agents cannot answer 'What time is checkout?' without calling the host.",
        ))
    if scores.conflict_free <= 0:
        flags.append(AEOFlag(
            severity="CRITICAL",
            code="material_policy_conflict",
            message="Structured data contradicts prose on a material policy field.",
            plain_english="Guests will receive incorrect policy information from AI booking agents.",
        ))
    if not schema.get("x-str-cancellation-policy", {}).get("tier"):
        flags.append(AEOFlag(
            severity="HIGH",
            code="cancellation_prose_only",
            message="Cancellation policy not machine-readable.",
            plain_english="AI agents must parse unstructured text, risking incorrect cancellation terms.",
        ))
    if not schema.get("x-str-min-stay"):
        flags.append(AEOFlag(
            severity="HIGH",
            code="min_stay_missing",
            message="Minimum stay not present as a structured field.",
            plain_english="Short-stay queries may surface this property incorrectly.",
        ))
    return flags


def _build_json_ld(req: AEOAuditRequest) -> dict:
    """Build a schema.org/LodgingBusiness JSON-LD block from available data."""
    s = req.existing_schema
    amenities = req.amenities_list
    return {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "name": s.get("name", ""),
        "description": req.listing_text[:200],
        "address": s.get("address", {}),
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": a, "value": True}
            for a in amenities
        ],
        "checkinTime": s.get("checkinTime", ""),
        "checkoutTime": s.get("checkoutTime", ""),
        "petsAllowed": s.get("petsAllowed", False),
        "smokingAllowed": s.get("smokingAllowed", False),
        "x-str-pet-policy": s.get("x-str-pet-policy", {}),
        "x-str-cancellation-policy": s.get("x-str-cancellation-policy", {}),
        "x-str-parking": s.get("x-str-parking", {}),
        "x-str-max-occupancy": s.get("x-str-max-occupancy"),
        "x-str-permit": s.get("x-str-permit", ""),
    }


def _build_optimized_opening(req: AEOAuditRequest) -> str:
    """Generate a machine-first listing opening from available structured data."""
    s = req.existing_schema
    rooms = s.get("numberOfRooms", "")
    occ = s.get("x-str-max-occupancy", "")
    city = s.get("address", {}).get("addressLocality", "")
    region = s.get("address", {}).get("addressRegion", "")
    name = s.get("name", "")
    checkin = s.get("checkinTime", "")
    checkout = s.get("checkoutTime", "")
    permit = s.get("x-str-permit", "")
    pet = s.get("x-str-pet-policy", {})
    parking = s.get("x-str-parking", {})

    parts = []
    if rooms and occ:
        parts.append(f"{rooms}BR beach house, {city} {region}. {occ} guests max.")
    elif name:
        parts.append(f"{name}. {city}, {region}.")
    if checkin and checkout:
        parts.append(f"Check-in {checkin}, checkout {checkout}.")
    if pet.get("allowed") is False:
        parts.append("No pets.")
    elif pet.get("species"):
        fee = pet.get("feePerPetPerNight", "")
        parts.append(f"Pets: {', '.join(pet['species'])} only. ${fee}/night/pet.")
    if parking.get("available") is True:
        parts.append("Parking available.")
    if s.get("smokingAllowed") is False:
        parts.append("No smoking.")
    cancel = s.get("x-str-cancellation-policy", {})
    if cancel.get("fullRefundDaysBeforeArrival"):
        days = cancel["fullRefundDaysBeforeArrival"]
        parts.append(f"{days}-day cancellation policy.")
    if permit:
        parts.append(f"STR Permit {permit}.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Listing URL for Sweet Clementine -- used to route to the pre-seeded result.
_CLEMENTINE_URL: str = "https://www.airbnb.com/rooms/838634728141757030"
_DEMO_MODE: bool = os.environ.get("DEMO_MODE", "true").lower() == "true"


def audit_listing(req: AEOAuditRequest) -> AEOAuditResult:
    """Run the AEO audit for a listing.

    Sweet Clementine is returned from the pre-seeded canonical result so the
    demo is instant and reproducible without live API credentials.
    All other listings run the deterministic rubric directly.
    """
    # Pre-seeded path: Sweet Clementine demo cache
    if req.listing_url == _CLEMENTINE_URL or _is_sweet_clementine(req):
        return _SWEET_CLEMENTINE_RESULT

    # Live rubric path for all other listings
    return _run_rubric(req)


def _is_sweet_clementine(req: AEOAuditRequest) -> bool:
    """Return True if req appears to describe Sweet Clementine."""
    return "Sweet Clementine" in req.listing_text or "838634728141757030" in req.listing_url


def _run_rubric(req: AEOAuditRequest) -> AEOAuditResult:
    """Run the full AEO rubric for a non-cached listing."""
    d1 = _score_structure(req)
    d2 = _score_parseability(req)
    d3 = _score_description(req)
    d4 = _score_conflict_free(req)

    scores = DimensionScores(
        structure_completeness=d1,
        agent_parseability=d2,
        description_quality=d3,
        conflict_free=d4,
    )
    overall = d1 + d2 + d3 + d4
    flags = _build_flags(req, scores)
    json_ld = _build_json_ld(req)
    opening = _build_optimized_opening(req)
    reasoning = (
        f"Score {overall}/100. "
        f"Structure completeness ({d1}/25). "
        f"Agent parseability ({d2}/25). "
        f"Description quality ({d3}/25). "
        f"Conflict-free ({d4}/25)."
    )
    return AEOAuditResult(
        overall_score=overall,
        dimension_scores=scores,
        critical_flags=flags,
        optimized_opening=opening,
        json_ld_schema=json_ld,
        reasoning_trace=reasoning,
    )
