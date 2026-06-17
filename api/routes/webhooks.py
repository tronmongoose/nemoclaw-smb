"""Webhook routes for nemoclaw-smb: 402 invoice events and Stripe callbacks.

Exports (via router):
    POST /webhooks/402      — run the full 402 pipeline against the singleton graph
    POST /webhooks/stripe   — verify Stripe-Signature when secret is set, else require header presence
"""

import os
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
async def webhook_stripe(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    """Acknowledge a Stripe webhook.

    When STRIPE_WEBHOOK_SECRET is set and the stripe SDK is available, verifies the
    payload signature cryptographically (400 on mismatch). In demo/mock mode (no secret),
    requires the header to be present (400 if absent).
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if secret:
        try:
            import stripe as _stripe  # guarded: SDK may not be installed
        except ImportError:
            _stripe = None  # type: ignore[assignment]
        if _stripe is not None:
            if stripe_signature is None:
                raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
            payload = await request.body()
            try:
                _stripe.Webhook.construct_event(payload, stripe_signature, secret)
            except _stripe.error.SignatureVerificationError as exc:
                raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc
            return {"received": True}

    # Demo/mock mode: secret unset or SDK unavailable — require header presence only.
    if stripe_signature is None:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    return {"received": True}
