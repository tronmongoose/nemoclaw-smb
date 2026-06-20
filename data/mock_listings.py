"""data/mock_listings.py -- Canonical STR listing data and pre-seeded AEO results.

Two listings are defined here:
  (a) Sweet Clementine by the Sea (prop-001) -- low AEO score 51/100 with
      critical conflicts and missing metadata, exactly per the master brief.
  (b) The Pelican Cottage (prop-002) -- high AEO score 91/100, clean, all
      10 booking questions answerable, no conflicts.

The actual AEO scoring logic ships in a later wave (skills/aeo_skill). These
constants hold the canonical data and pre-seeded results for the demo.

Public API:
    LISTINGS        -- dict keyed by listing_id with full listing dicts
    CLEMENTINE_AEO  -- pre-seeded AEO result for Sweet Clementine (51/100)
    PELICAN_AEO     -- pre-seeded AEO result for The Pelican Cottage (91/100)
"""
from __future__ import annotations

LISTINGS: dict[str, dict] = {
    "prop-001": {
        "property_id": "prop-001",
        "title": "Sweet Clementine by the Sea",
        "airbnb_id": "838634728141757030",
        "city": "Oceanside",
        "state": "CA",
        "description": (
            "Enjoy a beautiful stay steps from the beach. Perfect for families and groups "
            "looking for a relaxing getaway in sunny Oceanside, CA. Dogs welcome!"
        ),
        "pet_policy": "dogs allowed",
        "check_in_instructions": None,
        "check_out_instructions": None,
        "house_rules": "No smoking. No parties.",
        "amenities": ["wifi", "pool", "bbq", "beach_access", "parking"],
        "max_guests": 8,
        "bedrooms": 3,
        "bathrooms": 2,
    },
    "prop-002": {
        "property_id": "prop-002",
        "title": "The Pelican Cottage - Oceanside Beach House",
        "airbnb_id": "112233445566778899",
        "city": "Oceanside",
        "state": "CA",
        "description": (
            "The Pelican Cottage is a charming 2-bedroom beach house steps from the Pacific. "
            "Check in is at 4pm; check out is at 11am. Pets are not allowed. "
            "Free parking in the private driveway. Fast wifi throughout."
        ),
        "pet_policy": "no pets",
        "check_in_instructions": "Self check-in via lockbox at 4pm. Code sent 24h before arrival.",
        "check_out_instructions": "Check out by 11am. Leave keys on kitchen counter.",
        "house_rules": "No smoking. No parties. No pets. Quiet hours after 10pm.",
        "amenities": ["wifi", "parking", "beach_access", "washer", "dryer", "full_kitchen"],
        "max_guests": 4,
        "bedrooms": 2,
        "bathrooms": 1,
    },
}

# Pre-seeded AEO result for Sweet Clementine -- scores per the master brief.
CLEMENTINE_AEO: dict = {
    "property_id": "prop-001",
    "overall_score": 51,
    "dimension_scores": {
        "completeness": 14,   # out of 25
        "accuracy": 11,       # out of 25
        "specificity": 16,    # out of 25
        "ai_readability": 10, # out of 25
    },
    "critical_flags": [
        {
            "flag": "pet_policy_conflict",
            "severity": "critical",
            "detail": (
                "Listing title/description says 'Dogs welcome' but house rules say 'No pets'. "
                "AI booking agents will surface this conflict and may decline to recommend."
            ),
        },
        {
            "flag": "check_in_missing",
            "severity": "high",
            "detail": "Check-in instructions are missing. Booking AI cannot answer arrival questions.",
        },
        {
            "flag": "check_out_missing",
            "severity": "high",
            "detail": "Check-out instructions are missing. Booking AI cannot answer departure questions.",
        },
    ],
    "optimized_opening": (
        "Sweet Clementine by the Sea is a 3-bedroom, 2-bathroom beach house in Oceanside, CA "
        "accommodating up to 8 guests. Located steps from the Pacific Ocean, the property "
        "features a private pool, BBQ, and dedicated parking. Check-in is at 4pm via keypad; "
        "check-out is at 11am. No pets. No smoking. Fast Wi-Fi included."
    ),
    "json_ld_schema": {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "name": "Sweet Clementine by the Sea",
        "description": (
            "3-bedroom beachfront vacation rental in Oceanside, CA for up to 8 guests."
        ),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Oceanside",
            "addressRegion": "CA",
            "addressCountry": "US",
        },
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "WiFi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Pool", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "BBQ", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Beach Access", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Parking", "value": True},
        ],
        "occupancy": {"@type": "QuantitativeValue", "maxValue": 8},
        "petsAllowed": False,
        "checkinTime": "16:00",
        "checkoutTime": "11:00",
    },
}

# Pre-seeded AEO result for The Pelican Cottage -- high-scoring clean listing.
PELICAN_AEO: dict = {
    "property_id": "prop-002",
    "overall_score": 91,
    "dimension_scores": {
        "completeness": 24,   # out of 25
        "accuracy": 23,       # out of 25
        "specificity": 22,    # out of 25
        "ai_readability": 22, # out of 25
    },
    "critical_flags": [],
    "booking_questions_answerable": [
        "What time is check-in?",
        "What time is check-out?",
        "Are pets allowed?",
        "Is parking available?",
        "Is Wi-Fi included?",
        "How many guests can stay?",
        "How many bedrooms?",
        "How many bathrooms?",
        "What is the smoking policy?",
        "How do I get the keys?",
    ],
    "optimized_opening": (
        "The Pelican Cottage is a 2-bedroom, 1-bathroom beach house in Oceanside, CA "
        "accommodating up to 4 guests. Self check-in at 4pm via keypad lockbox; "
        "check-out by 11am. No pets. No smoking. Free private parking and fast Wi-Fi."
    ),
    "json_ld_schema": {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "name": "The Pelican Cottage - Oceanside Beach House",
        "description": (
            "2-bedroom beach house in Oceanside, CA for up to 4 guests. "
            "Steps from the Pacific."
        ),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Oceanside",
            "addressRegion": "CA",
            "addressCountry": "US",
        },
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "WiFi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Parking", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Beach Access", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Washer", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Dryer", "value": True},
        ],
        "occupancy": {"@type": "QuantitativeValue", "maxValue": 4},
        "petsAllowed": False,
        "checkinTime": "16:00",
        "checkoutTime": "11:00",
    },
}
