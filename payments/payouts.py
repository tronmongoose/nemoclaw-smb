"""payments/payouts.py: Global Payouts wrapper for crew members (mocked).

Pays each crew member for a given month via a signed Carryall envelope and
a mocked Stripe Transfer. Audit entries are written as if real.

Public API:
    PayoutBatch: dataclass with per-member results
    PayoutRecord: dataclass for a single payout
    run_payouts(crew, month) -> PayoutBatch
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

from agent.audit_log import append_action
from payments.envelopes import sign_stripe_envelope

_logger = logging.getLogger(__name__)


@dataclass
class PayoutRecord:
    """Result of a single crew member payout."""

    crew_id: str
    crew_name: str
    amount_cents: int
    month: str
    transfer_id: str
    status: str
    backend: str


@dataclass
class PayoutBatch:
    """Aggregate result of a month-end payout run."""

    month: str
    records: list[PayoutRecord] = field(default_factory=list)
    total_cents: int = 0


def _stable_transfer_id(crew_id: str, month: str) -> str:
    """Return a deterministic mock transfer id."""
    raw = json.dumps([crew_id, month], sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"tr_{digest}"


def _pay_one(member: dict, month: str) -> PayoutRecord:
    """Issue a payout for one crew member and write audit entry."""
    crew_id = member["id"]
    crew_name = member["name"]
    amount_cents = member["rate_cents"]

    sign_stripe_envelope(
        "payout:transfer",
        {
            "crew_id": crew_id,
            "crew_name": crew_name,
            "amount_cents": amount_cents,
            "month": month,
        },
        agent_id="property-mgmt-agent",
        scopes=["payout:crew"],
    )

    transfer_id = _stable_transfer_id(crew_id, month)

    append_action(
        action="payment",
        vendor="stripe-payouts",
        amount=amount_cents / 100.0,
        decision="payout_sent",
        actor="property-mgmt-agent",
        metadata={
            "crew_id": crew_id,
            "crew_name": crew_name,
            "month": month,
            "transfer_id": transfer_id,
            "backend": "mock",
        },
    )

    _logger.info(
        "payout: crew=%s amount=%d month=%s transfer=%s",
        crew_id, amount_cents, month, transfer_id,
    )

    return PayoutRecord(
        crew_id=crew_id,
        crew_name=crew_name,
        amount_cents=amount_cents,
        month=month,
        transfer_id=transfer_id,
        status="paid",
        backend="mock",
    )


def run_payouts(crew: list[dict], month: str) -> PayoutBatch:
    """Pay each crew member for the given month.

    Signs an envelope and writes an audit entry per member. All Stripe
    Transfers are mocked. month should be "YYYY-MM".
    """
    #COMPLETION_DRIVE: assumes each crew member has a connected Stripe account in production
    batch = PayoutBatch(month=month)
    for member in crew:
        record = _pay_one(member, month)
        batch.records.append(record)
        batch.total_cents += record.amount_cents
    return batch
