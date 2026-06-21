"""payments/issuing.py: Stripe Issuing for single-use cleaner cards.

Issues MCC-restricted, same-day-expiry virtual cards for cleaner crew.
All Stripe calls are DEMO_MODE-mocked; audit entries are written as if real.
Raw PAN is never returned, logged, or stored; only the card token/id.

Public API:
    CleanerCardResult: dataclass returned by issue_cleaner_card
    RevokeResult: dataclass returned by revoke_card
    issue_cleaner_card(job_id, property_id, cleaner_id, amount_cents) -> CleanerCardResult
    revoke_card(card_id, reason) -> RevokeResult
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone

from agent.audit_log import append_action
from agent.interactions_log import append_interaction
from config.demo_mode import demo_mode
from payments.envelopes import sign_stripe_envelope

_logger = logging.getLogger(__name__)

# MCC codes: 7349 = cleaning services, 5251 = hardware/supply stores
CLEANER_MCC_LIST: list[str] = ["7349", "5251"]

DEFAULT_AMOUNT_CENTS: int = 7500  # $75.00


@dataclass
class CleanerCardResult:
    """Result of issuing a single-use cleaner card."""

    card_token: str
    card_id: str
    job_id: str
    property_id: str
    cleaner_id: str
    amount_cap_cents: int
    mcc_list: list[str]
    expiry_utc: str
    backend: str


@dataclass
class RevokeResult:
    """Result of revoking a cleaner card."""

    card_id: str
    reason: str
    status: str
    backend: str


def _stable_card_id(job_id: str, cleaner_id: str) -> str:
    """Return a deterministic mock card id from job and cleaner."""
    raw = json.dumps([job_id, cleaner_id], sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"ic_{digest}"


def _same_day_eod_utc() -> datetime:
    """Return today's 23:59:59 UTC as a datetime."""
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time(23, 59, 59), tzinfo=timezone.utc)


def issue_cleaner_card(
    job_id: str,
    property_id: str,
    cleaner_id: str,
    amount_cents: int = DEFAULT_AMOUNT_CENTS,
) -> CleanerCardResult:
    """Issue a single-use, MCC-restricted virtual card for a cleaner job.

    Signs a Carryall envelope before the (mocked) Stripe Issuing call.
    Audit entry records card_id, job_id, amount_cap, expiry, MCC list.
    Returns a card TOKEN (never the raw PAN).
    """
    #COMPLETION_DRIVE: assumes Stripe Issuing is available in the connected account
    expiry_dt = _same_day_eod_utc()
    expiry_str = expiry_dt.isoformat()

    envelope_payload = {
        "job_id": job_id,
        "property_id": property_id,
        "cleaner_id": cleaner_id,
        "amount_cents": amount_cents,
        "mcc_list": CLEANER_MCC_LIST,
        "expiry": expiry_str,
    }

    sign_stripe_envelope(
        "issuing:card:create",
        envelope_payload,
        agent_id="cleaner-subagent",
        scopes=["card:issue:cleaning"],
    )

    card_id = _stable_card_id(job_id, cleaner_id)
    card_token = f"tok_{card_id}"
    backend = "mock"

    if not demo_mode():  # pragma: no cover
        _logger.warning("Live Stripe Issuing not configured; falling back to mock")

    _logger.info(
        "issuing: card=%s job=%s property=%s cleaner=%s cap=%d expiry=%s mcc=%s backend=%s",
        card_id, job_id, property_id, cleaner_id, amount_cents, expiry_str,
        CLEANER_MCC_LIST, backend,
    )

    append_action(
        action="payment",
        vendor="stripe-issuing",
        amount=amount_cents / 100.0,
        decision="card_issued",
        actor="cleaner-subagent",
        metadata={
            "card_id": card_id,
            "card_token": card_token,
            "job_id": job_id,
            "property_id": property_id,
            "cleaner_id": cleaner_id,
            "amount_cap_cents": amount_cents,
            "mcc_list": CLEANER_MCC_LIST,
            "expiry": expiry_str,
            "backend": backend,
        },
    )

    result = CleanerCardResult(
        card_token=card_token,
        card_id=card_id,
        job_id=job_id,
        property_id=property_id,
        cleaner_id=cleaner_id,
        amount_cap_cents=amount_cents,
        mcc_list=CLEANER_MCC_LIST,
        expiry_utc=expiry_str,
        backend=backend,
    )
    try:
        append_interaction(
            sponsor="Stripe", op="card issue (Issuing for Agents)",
            segment="firm", status="ok", metadata={"amount_cents": result.amount_cap_cents},
        )
    except Exception:
        pass
    return result


def revoke_card(card_id: str, reason: str) -> RevokeResult:
    """Revoke a cleaner card and log the reason.

    Mocked in DEMO_MODE. Audit entry records reason and card_id.
    """
    backend = "mock"

    append_action(
        action="payment",
        vendor="stripe-issuing",
        amount=0.0,
        decision="card_revoked",
        actor="cleaner-subagent",
        metadata={"card_id": card_id, "reason": reason, "backend": backend},
    )

    _logger.info("issuing: revoked card=%s reason=%r backend=%s", card_id, reason, backend)

    return RevokeResult(
        card_id=card_id,
        reason=reason,
        status="canceled",
        backend=backend,
    )
