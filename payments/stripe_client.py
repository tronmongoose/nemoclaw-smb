"""
NemoClaw Stripe client — test-mode/mock payment interface.

Behavior: if STRIPE_SECRET_KEY is present in env AND the stripe SDK is importable,
a live (test-mode) path could be wired; today only the deterministic mock path is
shipped. Default is always mock. IDs are derived from a SHA-256 hash of
(vendor, amount, idempotency_key) so repeated calls with the same key are idempotent.

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
import os
from typing import Optional

STRIPE_MODE = "test"

# #COMPLETION_DRIVE: STRIPE_SECRET_KEY detection is structural scaffolding;
# actual Stripe SDK path is intentionally unimplemented for demo safety.
_STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")


def _stable_id(prefix: str, *parts) -> str:
    """Return a deterministic prefixed ID from hashing the given parts."""
    raw = json.dumps(parts, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"{prefix}_{digest}"


def pay(
    vendor: str,
    amount: float,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Charge a vendor; returns a PaymentIntent-shaped dict in test mode."""
    key = idempotency_key or f"{vendor}:{amount}"
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
    """Cancel a subscription for vendor; returns a Subscription-shaped dict."""
    sub_id = _stable_id("sub_test", vendor, "cancel")
    return {
        "id": sub_id,
        "vendor": vendor,
        "status": "canceled",
        "mode": STRIPE_MODE,
    }


def create_subscription(vendor: str, amount: float) -> dict:
    """Create a recurring subscription; returns a Subscription-shaped dict."""
    sub_id = _stable_id("sub_test", vendor, amount, "create")
    return {
        "id": sub_id,
        "vendor": vendor,
        "amount": amount,
        "status": "active",
        "mode": STRIPE_MODE,
    }


def collect_fee(amount: float, basis: str) -> dict:
    """Record NemoClaw's own revenue fee; returns a PaymentIntent-shaped dict."""
    fee_id = _stable_id("pi_test", "nemoclaw_fee", amount, basis)
    return {
        "id": fee_id,
        "amount": amount,
        "status": "succeeded",
        "mode": STRIPE_MODE,
        "basis": basis,
    }
