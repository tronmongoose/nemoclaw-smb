"""acts/property_mgmt_agent.py: Act II: Property Management Agent orchestrator.

Handles checkout-triggered cleaner card issuance (with C1-scoped NHI),
month-end crew payouts, UBP invoice calculation, and portfolio summary.

The C1 governance beat: on every checkout, a least-privilege NHI is issued
for the "cleaner-subagent" identity (scopes: ["card:issue:cleaning"]) and
authorized before any card is issued. This is the ConductorOne showcase path.

Public API:
    PortfolioSummary: dataclass with portfolio-level stats
    handle_checkout_event(property_id, checkout_date) -> CleanerCardResult
    run_month_end_payouts(month) -> PayoutBatch
    calculate_ubp_invoices(month) -> list[OwnerInvoice]
    get_portfolio_summary() -> PortfolioSummary
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from control_plane.c1_governance import authorize, issue_nhi
from data.mock_ledger import (
    CREW,
    CREW_AVAILABILITY,
    MONTHLY_REVENUE,
    PROPERTIES,
    PROPERTY_OCCUPANCY,
    PROPERTY_TURNOVER_STATE,
    STAGE_ROLE,
    TURNOVER_STAGES,
    list_properties_for_owner,
)
from payments.connect import ensure_owner_accounts
from payments.issuing import CleanerCardResult, issue_cleaner_card
from payments.metronome import OwnerInvoice, calculate_ubp
from payments.payouts import PayoutBatch, run_payouts

_logger = logging.getLogger(__name__)

_OWNER_IDS = list({p["owner_id"] for p in PROPERTIES.values()})

# Fixed "now" for the demo so turnover ages and stall durations are deterministic.
_DEMO_NOW = datetime(2026, 6, 15, 18, 0, 0, tzinfo=timezone.utc)


@dataclass
class PortfolioSummary:
    """Top-level view of the managed STR portfolio."""

    property_count: int
    owner_count: int
    total_monthly_revenue_cents: int
    property_ids: list[str] = field(default_factory=list)
    owner_ids: list[str] = field(default_factory=list)
    properties_by_owner: dict[str, list[str]] = field(default_factory=dict)


def handle_checkout_event(property_id: str, checkout_date: str) -> CleanerCardResult:
    """Issue a single-use cleaner card on guest checkout.

    C1 governance path: issues a least-privilege NHI for "cleaner-subagent"
    scoped to ["card:issue:cleaning"], then authorizes it before issuing.
    Raises PermissionError if the NHI authorization is denied.

    checkout_date is an ISO date string (YYYY-MM-DD), used to form the job_id.
    """
    #COMPLETION_DRIVE: assumes one cleaner assigned per property; round-robins in prod
    nhi = issue_nhi(
        "cleaner-subagent",
        scopes=["card:issue:cleaning"],
        ttl_seconds=3600,
    )

    allowed, reason = authorize(nhi, action="card:issue", resource="stripe-issuing")
    if not allowed:
        raise PermissionError(
            f"NHI authorization denied for cleaner-subagent on {property_id}: {reason}"
        )

    _logger.info(
        "checkout: property=%s date=%s nhi=%s authorized=%s",
        property_id, checkout_date, nhi["id"], allowed,
    )

    cleaner = _pick_cleaner(property_id)
    job_id = f"job-{property_id}-{checkout_date}"

    return issue_cleaner_card(
        job_id=job_id,
        property_id=property_id,
        cleaner_id=cleaner["id"],
    )


def _pick_cleaner(property_id: str) -> dict:
    """Return the assigned cleaner for a property (deterministic by property index).

    Filters CREW to cleaners only; cycles by property index.
    """
    cleaners = [m for m in CREW if m["role"] == "cleaner"]
    prop_ids = sorted(PROPERTIES.keys())
    idx = prop_ids.index(property_id) % len(cleaners)
    return cleaners[idx]


def run_month_end_payouts(month: str) -> PayoutBatch:
    """Pay all CREW members for the given month.

    Ensures Stripe Connect accounts exist for all owners before running payouts.
    month should be "YYYY-MM".
    """
    ensure_owner_accounts(_OWNER_IDS)
    return run_payouts(CREW, month)


def calculate_ubp_invoices(month: str) -> list[OwnerInvoice]:
    """Return UBP invoices for every owner for the given month."""
    return [calculate_ubp(owner_id, month) for owner_id in _OWNER_IDS]


def get_portfolio_summary() -> PortfolioSummary:
    """Return a PortfolioSummary across all 5 properties and 3 owners."""
    from data.mock_ledger import MONTHLY_REVENUE

    properties_by_owner: dict[str, list[str]] = {}
    for owner_id in _OWNER_IDS:
        properties_by_owner[owner_id] = list_properties_for_owner(owner_id)

    total_revenue = sum(MONTHLY_REVENUE.values())

    return PortfolioSummary(
        property_count=len(PROPERTIES),
        owner_count=len(_OWNER_IDS),
        total_monthly_revenue_cents=total_revenue,
        property_ids=sorted(PROPERTIES.keys()),
        owner_ids=sorted(_OWNER_IDS),
        properties_by_owner=properties_by_owner,
    )


# ---------------------------------------------------------------------------
# Turnover loop + stall detection (coordination, not payments)
# ---------------------------------------------------------------------------


@dataclass
class TurnoverEvent:
    """One property's turnover-loop state (checkout -> clean -> inspect -> ready)."""

    property_id: str
    property_name: str
    current_stage: str
    overall_status: str  # "ready" | "in_progress" | "stalled"
    stages: list[dict] = field(default_factory=list)


def _hours_since(updated_ts: str) -> float:
    """Hours between an ISO timestamp and the fixed demo now (clamped at >= 0)."""
    then = datetime.fromisoformat(updated_ts)
    return max(0.0, (_DEMO_NOW - then).total_seconds() / 3600.0)


def get_turnover(property_id: str | None = None) -> list[TurnoverEvent]:
    """Return turnover state for one property, or all properties when None."""
    pids = [property_id] if property_id else sorted(PROPERTY_TURNOVER_STATE.keys())
    events: list[TurnoverEvent] = []
    for pid in pids:
        state = PROPERTY_TURNOVER_STATE.get(pid)
        if state is None:
            continue
        stages = []
        for stage in TURNOVER_STAGES:
            s = state["stages"][stage]
            stages.append({
                "stage": stage,
                "role": STAGE_ROLE[stage],
                "status": s["status"],
                "actor": s["actor"],
                "hours_in_stage": round(_hours_since(s["updated_ts"]), 1),
            })
        overall = (
            "stalled" if any(s["status"] == "blocked" for s in stages)
            else "ready" if all(s["status"] == "done" for s in stages)
            else "in_progress"
        )
        events.append(TurnoverEvent(
            property_id=pid,
            property_name=PROPERTIES[pid]["name"],
            current_stage=state["current_stage"],
            overall_status=overall,
            stages=stages,
        ))
    return events


def detect_stalls() -> list[dict]:
    """Return blocked handoffs across the portfolio as {from -> to} actor pairs.

    A stall is a stage with status 'blocked'. The handoff is labeled by the role
    that just finished (prior stage) and the role now stuck (the blocked stage).
    'waiting' downstream stages are not-yet-reached, not stalls, and are excluded.
    """
    stalls: list[dict] = []
    for pid in sorted(PROPERTY_TURNOVER_STATE.keys()):
        state = PROPERTY_TURNOVER_STATE[pid]
        for i, stage in enumerate(TURNOVER_STAGES):
            s = state["stages"][stage]
            if s["status"] != "blocked":
                continue
            prior = TURNOVER_STAGES[i - 1] if i > 0 else stage
            stalls.append({
                "handoff_id": f"{pid}:{stage}",
                "property_id": pid,
                "property_name": PROPERTIES[pid]["name"],
                "stage": stage,
                "from_actor": STAGE_ROLE[prior],
                "to_actor": STAGE_ROLE[stage],
                "assigned_to": s["actor"],
                "reason": s.get("reason", f"{stage} blocked"),
                "hours_stalled": round(_hours_since(s["updated_ts"]), 1),
            })
    return stalls


# ---------------------------------------------------------------------------
# Performance flagging + cleaner scheduling (Hermes connective tissue)
# ---------------------------------------------------------------------------


def analyze_performance() -> list[dict]:
    """Rank each property against the portfolio revenue average (no LLM).

    Returns per-property {revenue, portfolio_avg, pct_vs_avg, status, occupancy}
    where status is over | under | on_track on a +/-15% band.
    """
    pids = sorted(PROPERTIES.keys())
    avg = sum(MONTHLY_REVENUE.get(p, 0) for p in pids) / max(1, len(pids))
    out: list[dict] = []
    for pid in pids:
        rev = MONTHLY_REVENUE.get(pid, 0)
        pct = (rev - avg) / avg if avg else 0.0
        status = "over" if pct > 0.15 else "under" if pct < -0.15 else "on_track"
        out.append({
            "property_id": pid,
            "property_name": PROPERTIES[pid]["name"],
            "revenue_cents": rev,
            "portfolio_avg_cents": int(avg),
            "pct_vs_avg": round(pct, 3),
            "status": status,
            "occupancy": PROPERTY_OCCUPANCY.get(pid, 0.0),
        })
    return out


def _cleaner_availability() -> list[dict]:
    """Return each cleaner's free-from time and whether they are free at _DEMO_NOW."""
    out: list[dict] = []
    for c in (m for m in CREW if m["role"] == "cleaner"):
        ff = CREW_AVAILABILITY.get(c["id"])
        available = ff is not None and datetime.fromisoformat(ff) <= _DEMO_NOW
        out.append({"id": c["id"], "name": c["name"], "free_from": ff, "available": available})
    return out


def clean_stalls() -> list[dict]:
    """Clean-stage stalls enriched with crew availability + a free cleaner to reassign to."""
    avail = _cleaner_availability()
    by_name = {a["name"]: a for a in avail}
    free = [a for a in avail if a["available"]]
    out: list[dict] = []
    for h in detect_stalls():
        if h["stage"] != "clean":
            continue
        suggested = next((a for a in free if a["name"] != h["assigned_to"]), None)
        out.append({
            **h,
            "assigned_cleaner": by_name.get(h["assigned_to"]),
            "suggested_cleaner": suggested,
            "crew_availability": avail,
        })
    return out
