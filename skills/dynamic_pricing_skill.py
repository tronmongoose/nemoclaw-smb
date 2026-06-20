"""skills/dynamic_pricing_skill.py -- Dynamic pricing recommendation skill.

Synthesizes occupancy, local events, comp-set rates, seasonality, and day-of-week
into a nightly rate recommendation. The reasoning trace routes to Nemotron Ultra
(config/model_routing: task "dynamic_pricing") but is DEMO_MODE-cached so no live
call is required.

Mock inputs include three Oceanside comps and local events (Comic-Con, Farmers
Market, holiday weekends) that exercise the full signal-synthesis path.

Public API:
    PricingRequest          -- input dataclass
    PricingRecommendation   -- output dataclass
    recommend_price(req)    -- PricingRequest -> PricingRecommendation
    OCEANSIDE_COMPS         -- three Oceanside comp-set mock listings
    LOCAL_EVENTS            -- local-event mock inputs (Comic-Con + others)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from config.demo_mode import demo_mode
from config.model_routing import route_for
from agent.nvidia_client import call_nemotron

# ---------------------------------------------------------------------------
# Mock comp-set: three Oceanside comps used when caller supplies an empty comp set.
# ---------------------------------------------------------------------------

OCEANSIDE_COMPS: List[dict] = [
    {
        "name": "Surf Shack Oceanside",
        "bedrooms": 2,
        "base_rate": 185,
        "current_rate": 195,
        "occupancy_rate": 0.78,
    },
    {
        "name": "Strand Breeze Cottage",
        "bedrooms": 2,
        "base_rate": 210,
        "current_rate": 230,
        "occupancy_rate": 0.82,
    },
    {
        "name": "Pacific Hideaway",
        "bedrooms": 3,
        "base_rate": 240,
        "current_rate": 265,
        "occupancy_rate": 0.71,
    },
]

# ---------------------------------------------------------------------------
# Mock local events that drive rate uplift when present.
# ---------------------------------------------------------------------------

LOCAL_EVENTS: List[dict] = [
    {
        "name": "Comic-Con International",
        "city": "San Diego",
        "uplift_multiplier": 1.45,
        "typical_months": [7],
        "typical_days_of_week": ["fri", "sat", "sun"],
    },
    {
        "name": "Oceanside Farmers Market",
        "city": "Oceanside",
        "uplift_multiplier": 1.10,
        "typical_months": list(range(1, 13)),
        "typical_days_of_week": ["sat"],
    },
    {
        "name": "Holiday Weekend",
        "city": "Oceanside",
        "uplift_multiplier": 1.30,
        "typical_months": [5, 7, 9, 11],
        "typical_days_of_week": ["fri", "sat", "sun"],
    },
]

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PricingRequest:
    """Input to the dynamic pricing skill."""

    property_id: str
    current_rate: float            # current nightly rate in USD
    occupancy_rate: float          # trailing 30-day occupancy (0.0 to 1.0)
    local_events: List[str]        # names of upcoming local events
    comp_set_rates: List[float]    # current nightly rates from comparable listings
    season: str                    # "peak", "shoulder", or "off"
    day_of_week: str               # "mon", "tue", "wed", "thu", "fri", "sat", "sun"


@dataclass
class PricingRecommendation:
    """Output from the dynamic pricing skill."""

    recommended_rate: float
    confidence: str                # "high", "medium", "low"
    reasoning: str
    suggested_title_tweak: str
    valid_for_hours: int


# ---------------------------------------------------------------------------
# Signal synthesis helpers (deterministic logic, no LLM dependency)
# ---------------------------------------------------------------------------

_SEASON_MULTIPLIERS: dict[str, float] = {
    "peak": 1.25,
    "shoulder": 1.05,
    "off": 0.85,
}

_WEEKEND_DAYS = {"fri", "sat", "sun"}

_OCCUPANCY_BANDS: list[tuple[float, float]] = [
    # (threshold, multiplier): applied when occupancy >= threshold
    (0.85, 1.20),
    (0.70, 1.08),
    (0.50, 1.00),
    (0.30, 0.90),
    (0.00, 0.80),
]


def _occupancy_multiplier(rate: float) -> float:
    """Return rate multiplier based on occupancy band."""
    for threshold, mult in _OCCUPANCY_BANDS:
        if rate >= threshold:
            return mult
    return 0.80


def _event_multiplier(event_names: List[str]) -> float:
    """Return the maximum uplift multiplier from the active event list."""
    upper_names = {e.upper() for e in event_names}
    best = 1.0
    for ev in LOCAL_EVENTS:
        if ev["name"].upper() in upper_names:
            best = max(best, ev["uplift_multiplier"])
    return best


def _comp_anchor(comp_rates: List[float]) -> float:
    """Return the comp-set median rate, or 0 if no comps provided."""
    if not comp_rates:
        return 0.0
    sorted_rates = sorted(comp_rates)
    mid = len(sorted_rates) // 2
    if len(sorted_rates) % 2 == 0:
        return (sorted_rates[mid - 1] + sorted_rates[mid]) / 2
    return sorted_rates[mid]


def _blend_rate(
    current_rate: float,
    signal_rate: float,
    comp_anchor: float,
) -> float:
    """Blend signal-adjusted rate with comp anchor (60/40 if anchor available)."""
    if comp_anchor > 0:
        return round(0.60 * signal_rate + 0.40 * comp_anchor, 2)
    return round(signal_rate, 2)


def _confidence(occupancy: float, event_count: int, comp_count: int) -> str:
    """Assess recommendation confidence from input signal richness."""
    score = 0
    if comp_count >= 2:
        score += 2
    elif comp_count == 1:
        score += 1
    if occupancy > 0.0:
        score += 1
    if event_count > 0:
        score += 1
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _build_reasoning(req: PricingRequest, raw_rate: float, final_rate: float) -> str:
    """Compose the deterministic reasoning trace (no LLM call in DEMO_MODE)."""
    occ_mult = _occupancy_multiplier(req.occupancy_rate)
    season_mult = _SEASON_MULTIPLIERS.get(req.season, 1.0)
    event_mult = _event_multiplier(req.local_events)
    weekend_note = "weekend uplift applied" if req.day_of_week in _WEEKEND_DAYS else "weekday base"
    comp_note = (
        f"comp-set anchor ${_comp_anchor(req.comp_set_rates):.0f} from {len(req.comp_set_rates)} comps"
        if req.comp_set_rates
        else "no comp-set provided; signal-only pricing"
    )
    events_note = (
        ", ".join(req.local_events) if req.local_events else "no local events"
    )
    return (
        f"Base ${req.current_rate:.0f}. "
        f"Season={req.season} (x{season_mult:.2f}). "
        f"Occupancy={req.occupancy_rate:.0%} (x{occ_mult:.2f}). "
        f"Events: {events_note} (x{event_mult:.2f}). "
        f"{weekend_note}. "
        f"Signal rate ${raw_rate:.0f}. "
        f"{comp_note}. "
        f"Recommended ${final_rate:.0f}."
    )


def _title_tweak(req: PricingRequest, final_rate: float) -> str:
    """Generate a brief title tweak reflecting current demand signal."""
    if req.local_events:
        event_name = req.local_events[0]
        return f"Perfect for {event_name} -- book now at ${final_rate:.0f}/night"
    if req.season == "peak":
        return f"Peak season available -- ${final_rate:.0f}/night"
    if req.occupancy_rate >= 0.80:
        return f"Limited availability at ${final_rate:.0f}/night"
    return f"Great value at ${final_rate:.0f}/night this {req.day_of_week.title()}"


# ---------------------------------------------------------------------------
# DEMO_MODE cached reasoning string (routes to Nemotron path, returns mock)
# ---------------------------------------------------------------------------

def _demo_reasoning_trace(req: PricingRequest, final_rate: float) -> str:
    """Return the Nemotron reasoning trace, using cached mock in DEMO_MODE."""
    model = route_for("dynamic_pricing")
    if demo_mode():
        # Deterministic, no live call -- cache satisfies demo requirement
        return (
            f"[{model}/demo-cached] "
            + _build_reasoning(req, final_rate, final_rate)
        )
    prompt = (
        f"You are a professional STR revenue manager. "
        f"Property {req.property_id}. Current rate ${req.current_rate}. "
        f"Occupancy {req.occupancy_rate:.0%}, season={req.season}, "
        f"day={req.day_of_week}, events={req.local_events}. "
        f"Comp rates: {req.comp_set_rates}. "
        f"Recommended rate: ${final_rate}. "
        f"Explain in 2 sentences why this rate is correct."
    )
    return call_nemotron(prompt, max_tokens=256, temperature=0.0)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def recommend_price(req: PricingRequest) -> PricingRecommendation:
    """Synthesize pricing signals into a nightly rate recommendation.

    Blends occupancy band, season, local events, comp-set median, and
    day-of-week into a single rate. Reasoning routes through Nemotron Ultra
    but is DEMO_MODE-cached for deterministic demo operation.
    #COMPLETION_DRIVE: comp_set_rates may be empty; falls back to OCEANSIDE_COMPS rates.
    """
    comps = req.comp_set_rates if req.comp_set_rates else [c["current_rate"] for c in OCEANSIDE_COMPS]
    season_mult = _SEASON_MULTIPLIERS.get(req.season, 1.0)
    occ_mult = _occupancy_multiplier(req.occupancy_rate)
    event_mult = _event_multiplier(req.local_events)
    weekend_mult = 1.12 if req.day_of_week in _WEEKEND_DAYS else 1.0

    raw_rate = req.current_rate * season_mult * occ_mult * event_mult * weekend_mult
    comp_anchor = _comp_anchor(comps)
    final_rate = _blend_rate(req.current_rate, raw_rate, comp_anchor)

    reasoning = _demo_reasoning_trace(req, final_rate)
    conf = _confidence(req.occupancy_rate, len(req.local_events), len(comps))
    title = _title_tweak(req, final_rate)

    return PricingRecommendation(
        recommended_rate=final_rate,
        confidence=conf,
        reasoning=reasoning,
        suggested_title_tweak=title,
        valid_for_hours=12,
    )
