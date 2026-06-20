"""tests/test_aeo.py -- AEO skill assertions per the master brief.

All tests pass with DEMO_MODE=true and no live API credentials.
Sweet Clementine uses the pre-seeded canonical result.
Pelican Cottage runs through the live deterministic rubric.
"""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("DEMO_MODE", "true")

from skills.aeo_skill import (
    AEOAuditRequest,
    AEOAuditResult,
    audit_listing,
)
from data.mock_listings import LISTINGS

# ---------------------------------------------------------------------------
# Sweet Clementine -- pre-seeded path
# ---------------------------------------------------------------------------

_CLEMENTINE_URL = "https://www.airbnb.com/rooms/838634728141757030"
_CLEMENTINE_LISTING = LISTINGS["prop-001"]


def _clementine_req() -> AEOAuditRequest:
    """Build the canonical AEOAuditRequest for Sweet Clementine."""
    return AEOAuditRequest(
        listing_text=(
            "Hey Future Guests :) Welcome to Sweet Clementine by the Sea! "
            "This pet-friendly home is perfect for your next beach getaway. "
            "Come experience all that Oceanside has to offer. "
            "House rules: We only accept dogs. No smoking. No parties. "
            "Cancellation: full refund if cancelled 30 days before arrival. "
            "Free parking on premises. Outdoor space includes fire pit and fenced backyard. "
            "STR Permit 018234. Note: minor construction two doors down."
        ),
        amenities_list=[
            "wifi", "kitchen", "washer_dryer", "fire_pit",
            "fenced_backyard", "smart_tv", "parking",
        ],
        existing_schema={},
        listing_url=_CLEMENTINE_URL,
    )


@pytest.fixture
def clementine_result() -> AEOAuditResult:
    """Pre-seeded AEO result for Sweet Clementine."""
    return audit_listing(_clementine_req())


def test_clementine_overall_score_in_range(clementine_result: AEOAuditResult) -> None:
    """Overall score must be between 45 and 57 (master brief canonical: 51)."""
    assert 45 <= clementine_result.overall_score <= 57, (
        f"Expected overall score in [45, 57], got {clementine_result.overall_score}"
    )


def test_clementine_dimension_scores(clementine_result: AEOAuditResult) -> None:
    """Dimension sub-scores must match the master brief: 14/11/16/10."""
    ds = clementine_result.dimension_scores
    assert ds.structure_completeness == 14, f"Expected 14, got {ds.structure_completeness}"
    assert ds.agent_parseability == 11, f"Expected 11, got {ds.agent_parseability}"
    assert ds.description_quality == 16, f"Expected 16, got {ds.description_quality}"
    assert ds.conflict_free == 10, f"Expected 10, got {ds.conflict_free}"


def test_clementine_dog_only_conflict_flag(clementine_result: AEOAuditResult) -> None:
    """CRITICAL pet species conflict flag must be present in critical_flags."""
    codes = [f.code for f in clementine_result.critical_flags]
    assert "pet_species_conflict" in codes, (
        f"Expected 'pet_species_conflict' in flags, got codes: {codes}"
    )
    conflict_flag = next(f for f in clementine_result.critical_flags if f.code == "pet_species_conflict")
    assert conflict_flag.severity == "CRITICAL"
    # plain_english must explain a cat owner would be turned away
    assert "cat" in conflict_flag.plain_english.lower() or "turned away" in conflict_flag.plain_english.lower()


def test_clementine_checkin_flag_critical(clementine_result: AEOAuditResult) -> None:
    """CRITICAL check-in time flag must be present."""
    codes = [f.code for f in clementine_result.critical_flags]
    assert "checkin_time_missing" in codes, (
        f"Expected 'checkin_time_missing' flag, got: {codes}"
    )
    flag = next(f for f in clementine_result.critical_flags if f.code == "checkin_time_missing")
    assert flag.severity == "CRITICAL"


def test_clementine_checkout_flag_critical(clementine_result: AEOAuditResult) -> None:
    """CRITICAL checkout time flag must be present."""
    codes = [f.code for f in clementine_result.critical_flags]
    assert "checkout_time_missing" in codes, (
        f"Expected 'checkout_time_missing' flag, got: {codes}"
    )
    flag = next(f for f in clementine_result.critical_flags if f.code == "checkout_time_missing")
    assert flag.severity == "CRITICAL"


def test_clementine_json_ld_valid_dict(clementine_result: AEOAuditResult) -> None:
    """JSON-LD must be a valid Python dict with required schema.org fields."""
    schema = clementine_result.json_ld_schema
    assert isinstance(schema, dict), "json_ld_schema must be a dict"
    assert schema.get("@context") == "https://schema.org"
    assert schema.get("@type") == "LodgingBusiness"
    assert "name" in schema
    assert "address" in schema
    assert "checkinTime" in schema
    assert "checkoutTime" in schema
    assert "petsAllowed" in schema


def test_clementine_json_ld_pet_species(clementine_result: AEOAuditResult) -> None:
    """x-str-pet-policy.species must be exactly ['dogs']."""
    pet = clementine_result.json_ld_schema.get("x-str-pet-policy", {})
    assert pet.get("species") == ["dogs"], (
        f"Expected species=['dogs'], got {pet.get('species')}"
    )


def test_clementine_json_ld_cameras(clementine_result: AEOAuditResult) -> None:
    """JSON-LD must include x-str-cameras disclosure field."""
    schema = clementine_result.json_ld_schema
    assert "x-str-cameras" in schema, "Expected x-str-cameras in JSON-LD"
    cameras = schema["x-str-cameras"]
    assert cameras.get("exterior") is True


def test_clementine_json_ld_construction(clementine_result: AEOAuditResult) -> None:
    """JSON-LD must include x-str-active-construction-nearby field."""
    schema = clementine_result.json_ld_schema
    assert schema.get("x-str-active-construction-nearby") is True


def test_clementine_optimized_opening_no_hey(clementine_result: AEOAuditResult) -> None:
    """Optimized opening must not start with 'Hey'."""
    opening = clementine_result.optimized_opening
    assert not opening.startswith("Hey"), (
        f"Opening must not start with 'Hey', got: {opening[:50]}"
    )


def test_clementine_optimized_opening_starts_with_facts(clementine_result: AEOAuditResult) -> None:
    """Optimized opening must lead with bedroom/location facts."""
    opening = clementine_result.optimized_opening[:80].lower()
    has_facts = any(k in opening for k in ["br", "bedroom", "2br", "3br", "beach", "cottage", "oceanside"])
    assert has_facts, f"Opening should start with bedroom/location facts, got: {opening}"


# ---------------------------------------------------------------------------
# Pelican Cottage -- live rubric path (must score > 85)
# ---------------------------------------------------------------------------

_PELICAN_LISTING = LISTINGS["prop-002"]


def _pelican_req() -> AEOAuditRequest:
    """Build an AEOAuditRequest for Pelican Cottage with full structured schema.

    This represents the 'after' state: all 10 booking questions answerable,
    no conflicts, full JSON-LD present.
    """
    return AEOAuditRequest(
        listing_text=(
            "2BR/1BA beach house, Oceanside CA. 4 guests max. 5-min walk to Strand Beach. "
            "Check-in at 4pm via self-service lockbox. Check out by 11am. "
            "No pets allowed. No smoking on the entire property. "
            "30-day cancellation policy: full refund if cancelled 30 days before arrival. "
            "Free parking in the private driveway. Fast wifi throughout. "
            "Outdoor space: front deck with ocean views. "
            "STR Permit 019988."
        ),
        amenities_list=[
            "wifi", "parking", "beach_access", "washer", "dryer",
            "full_kitchen", "deck", "outdoor",
        ],
        existing_schema={
            "@context": "https://schema.org",
            "@type": "LodgingBusiness",
            "name": "The Pelican Cottage - Oceanside Beach House",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Oceanside",
                "addressRegion": "CA",
                "addressCountry": "US",
            },
            "numberOfRooms": 2,
            "checkinTime": "16:00",
            "checkoutTime": "11:00",
            "petsAllowed": False,
            "smokingAllowed": False,
            "x-str-permit": "019988",
            "x-str-pet-policy": {
                "allowed": False,
                "species": [],
                "feePerPetPerNight": 0,
                "currency": "USD",
            },
            "x-str-cancellation-policy": {
                "tier": "moderate",
                "fullRefundDaysBeforeArrival": 30,
                "noRefundWithin": 14,
                "earlyDepartureRefund": False,
            },
            "x-str-parking": {
                "available": True,
                "type": ["driveway"],
                "smallCarOnly": False,
                "notes": "Private driveway, fits 2 cars.",
            },
            "x-str-quiet-hours": {"start": "22:00", "end": "08:00"},
            "x-str-max-occupancy": 4,
            "x-str-min-stay": 2,
        },
        listing_url="https://www.airbnb.com/rooms/112233445566778899",
    )


@pytest.fixture
def pelican_result() -> AEOAuditResult:
    """Live-rubric AEO result for Pelican Cottage."""
    return audit_listing(_pelican_req())


def test_pelican_score_above_85(pelican_result: AEOAuditResult) -> None:
    """Pelican Cottage must score above 85 (well-optimized listing)."""
    assert pelican_result.overall_score > 85, (
        f"Pelican Cottage should score > 85, got {pelican_result.overall_score}. "
        f"Dimension breakdown: {pelican_result.dimension_scores}"
    )


def test_pelican_no_critical_flags(pelican_result: AEOAuditResult) -> None:
    """A fully-structured listing should have no CRITICAL flags."""
    critical = [f for f in pelican_result.critical_flags if f.severity == "CRITICAL"]
    assert len(critical) == 0, (
        f"Pelican Cottage should have no CRITICAL flags, got: {[f.code for f in critical]}"
    )


def test_pelican_json_ld_is_dict(pelican_result: AEOAuditResult) -> None:
    """Pelican JSON-LD must be a valid dict."""
    assert isinstance(pelican_result.json_ld_schema, dict)
    assert pelican_result.json_ld_schema.get("@context") == "https://schema.org"


def test_pelican_opening_no_hey(pelican_result: AEOAuditResult) -> None:
    """Pelican optimized opening must not start with 'Hey'."""
    assert not pelican_result.optimized_opening.startswith("Hey")
