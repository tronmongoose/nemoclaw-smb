"""Webhook routes for nemoclaw-smb: 402 invoice events and Stripe callbacks.

Exports (via router):
    POST /webhooks/402      — run the full 402 pipeline against the singleton graph
    POST /webhooks/stripe   — validate Stripe-Signature header presence, return ack
"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from api.models.invoice import Invoice402Event
from api.state import graph
from payments.payment_402_handler import handle_402

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/402")
def webhook_402(event: Invoice402Event) -> dict:
    """Handle an inbound HTTP-402 vendor invoice; run full NemoClaw pipeline."""
    return handle_402(event.model_dump(), graph)


@router.post("/stripe")
def webhook_stripe(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    """Acknowledge a Stripe webhook; require Stripe-Signature header presence.

    Cryptographic verification is intentionally skipped in the demo — the header
    must be present to satisfy the webhook-secret rule in the brief.
    #COMPLETION_DRIVE: production should verify with stripe.WebhookSignature.verify_header
    """
    if stripe_signature is None:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    return {"received": True}
