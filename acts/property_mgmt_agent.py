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

from control_plane.c1_governance import authorize, issue_nhi
from data.mock_ledger import CREW, PROPERTIES, list_properties_for_owner
from payments.connect import ensure_owner_accounts
from payments.issuing import CleanerCardResult, issue_cleaner_card
from payments.metronome import OwnerInvoice, calculate_ubp
from payments.payouts import PayoutBatch, run_payouts

_logger = logging.getLogger(__name__)

_OWNER_IDS = list({p["owner_id"] for p in PROPERTIES.values()})


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
