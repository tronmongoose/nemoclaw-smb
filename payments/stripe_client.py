"""
NemoClaw Stripe client — test-mode/mock payment interface.

Behavior:
- If STRIPE_SECRET_KEY is present in env AND begins with "sk_test_", the live Stripe
  test-mode SDK path is taken (PaymentIntent, Subscription, etc.).
- sk_live_ keys are explicitly refused — this is a hackathon project and live-mode
  charges would be a safety hazard.
- Any Stripe SDK error or missing key falls through to the deterministic mock path;
  callers are never raised-to.

Public API:
    pay(vendor, amount, idempotency_key) -> dict
    cancel_subscription(vendor) -> dict
    create_subscription(vendor, amount) -> dict
    collect_fee(amount, basis) -> dict

Constant:
    STRIPE_MODE = "test"
"""

import hashlib
import json
import logging
import os
from typing import Optional

STRIPE_MODE = "test"

logger = logging.getLogger(__name__)

_STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

# Test-mode payment method id per docs.stripe.com/testing#cards
_TEST_PM = "pm_card_visa"


def _is_live_key(key: str) -> bool:
    """Return True if the key is a live-mode Stripe key."""
    return key.startswith("sk_live_")


def _is_test_key(key: str) -> bool:
    """Return True if the key is a valid test-mode Stripe key."""
    return key.startswith("sk_test_")


def _stable_id(prefix: str, *parts) -> str:
    """Return a deterministic prefixed ID from hashing the given parts."""
    raw = json.dumps(parts, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _get_stripe():
    """
    Import stripe and set the API key; return the module or None.

    Refuses live-mode keys unconditionally — test mode only.
    Returns None when key is absent, invalid, or SDK import fails.
    """
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if _is_live_key(key):
        # #SUGGEST_VERIFY: confirm no live key ever lands in .env for this project
        logger.warning(
            "STRIPE_SECRET_KEY is a live-mode key (sk_live_). "
            "NemoClaw refuses live-mode operations — falling back to mock."
        )
        return None
    if not _is_test_key(key):
        return None
    try:
        import stripe as _stripe  # noqa: PLC0415
        _stripe.api_key = key
        return _stripe
    except ImportError:
        logger.warning("stripe SDK not importable; using mock path")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pay(
    vendor: str,
    amount: float,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Charge a vendor via PaymentIntent; returns a PaymentIntent-shaped dict.

    Live path: stripe.PaymentIntent.create(amount_cents, currency, payment_method,
    confirm=True). Mock path: deterministic id from sha256(vendor, amount, key).
    amount is in dollars; converted to cents for Stripe.
    """
    key = idempotency_key or f"{vendor}:{amount}"
    stripe = _get_stripe()
    if stripe is not None:
        try:
            amount_cents = int(round(amount * 100))
            pi = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                payment_method=_TEST_PM,
                confirm=True,
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                idempotency_key=key,
            )
            return {
                "id": pi.id,
                "status": pi.status,
                "amount": amount,
                "vendor": vendor,
                "mode": STRIPE_MODE,
                "livemode": False,
            }
        except Exception as exc:
            logger.warning("Stripe pay failed (%s); using mock", exc)

    pi_id = _stable_id("pi_test", vendor, amount, key)
    return {
        "id": pi_id,
        "status": "succeeded",
        "amount": amount,
        "vendor": vendor,
        "mode": STRIPE_MODE,
        "livemode": False,
    }


def cancel_subscription(vendor: str) -> dict:
    """Cancel a subscription for vendor; returns a Subscription-shaped dict.

    Mock only — cancellation requires a stored subscription id; the mock
    path produces a deterministic id so callers stay stable.
    #COMPLETION_DRIVE: live cancel would require persisting sub ids from create_subscription.
    """
    sub_id = _stable_id("sub_test", vendor, "cancel")
    return {
        "id": sub_id,
        "vendor": vendor,
        "status": "canceled",
        "mode": STRIPE_MODE,
    }


def create_subscription(vendor: str, amount: float) -> dict:
    """Provision a Stripe subscription (Product + Price + Subscription).

    Live path: creates a Product, a recurring monthly Price (amount in cents),
    and a Subscription with a test Customer. Mock path: deterministic id.
    amount is monthly dollars.
    """
    stripe = _get_stripe()
    if stripe is not None:
        try:
            amount_cents = int(round(amount * 100))
            product = stripe.Product.create(name=f"NemoClaw SaaS — {vendor}")
            price = stripe.Price.create(
                product=product.id,
                unit_amount=amount_cents,
                currency="usd",
                recurring={"interval": "month"},
            )
            customer = stripe.Customer.create(
                name=f"nemoclaw-smb:{vendor}",
                metadata={"vendor": vendor},
            )
            sub = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price.id}],
            )
            return {
                "id": sub.id,
                "vendor": vendor,
                "amount": amount,
                "status": sub.status,
                "mode": STRIPE_MODE,
            }
        except Exception as exc:
            logger.warning("Stripe create_subscription failed (%s); using mock", exc)

    sub_id = _stable_id("sub_test", vendor, amount, "create")
    return {
        "id": sub_id,
        "vendor": vendor,
        "amount": amount,
        "status": "active",
        "mode": STRIPE_MODE,
    }


def collect_fee(amount: float, basis: str) -> dict:
    """Record NemoClaw's own 0.5% revenue fee via a test-mode PaymentIntent.

    Live path: stripe.PaymentIntent.create for the fee amount (in cents).
    Mock path: deterministic id.
    amount is in dollars.
    """
    stripe = _get_stripe()
    if stripe is not None:
        try:
            amount_cents = int(round(amount * 100))
            pi = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                payment_method=_TEST_PM,
                confirm=True,
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                metadata={"basis": basis, "fee_type": "nemoclaw_platform_fee"},
            )
            return {
                "id": pi.id,
                "amount": amount,
                "status": pi.status,
                "mode": STRIPE_MODE,
                "basis": basis,
            }
        except Exception as exc:
            logger.warning("Stripe collect_fee failed (%s); using mock", exc)

    fee_id = _stable_id("pi_test", "nemoclaw_fee", amount, basis)
    return {
        "id": fee_id,
        "amount": amount,
        "status": "succeeded",
        "mode": STRIPE_MODE,
        "basis": basis,
    }
