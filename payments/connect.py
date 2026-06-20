"""payments/connect.py -- Stripe Connect multi-owner connected accounts (mocked).

Each STR property owner gets a Stripe Connect account so payouts flow to their
bank. All Stripe API calls are mocked in DEMO_MODE.

Public API:
    ConnectedAccount   -- dataclass representing an owner's Stripe account
    ensure_owner_accounts(owners) -> dict[owner_id, ConnectedAccount]
    get_connected_account(owner_id) -> ConnectedAccount | None
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

from agent.audit_log import append_action
from config.demo_mode import demo_mode

_logger = logging.getLogger(__name__)

# Module-level cache: owner_id -> ConnectedAccount
_account_cache: dict[str, "ConnectedAccount"] = {}


@dataclass
class ConnectedAccount:
    """A Stripe Connect account for one STR property owner."""

    owner_id: str
    stripe_account_id: str
    status: str
    backend: str


def _stable_account_id(owner_id: str) -> str:
    """Return a deterministic mock Stripe account id for an owner."""
    raw = json.dumps([owner_id], sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"acct_{digest}"


def _provision(owner_id: str) -> ConnectedAccount:
    """Provision (mock) and cache a Stripe Connect account for owner_id."""
    #COMPLETION_DRIVE: live path would call stripe.Account.create(type="express")
    backend = "mock"
    if not demo_mode():  # pragma: no cover
        _logger.warning("Live Stripe Connect provisioning not configured; using mock for %s", owner_id)

    account_id = _stable_account_id(owner_id)
    account = ConnectedAccount(
        owner_id=owner_id,
        stripe_account_id=account_id,
        status="active",
        backend=backend,
    )
    _account_cache[owner_id] = account

    append_action(
        action="access_change",
        vendor="stripe-connect",
        amount=0.0,
        decision="account_provisioned",
        actor="property-mgmt-agent",
        metadata={
            "owner_id": owner_id,
            "stripe_account_id": account_id,
            "backend": backend,
        },
    )

    _logger.info("connect: provisioned owner=%s account=%s", owner_id, account_id)
    return account


def ensure_owner_accounts(owners: list[str]) -> dict[str, ConnectedAccount]:
    """Return a mapping of owner_id to ConnectedAccount for all owners.

    Provisions accounts for any owner not already cached.
    """
    result: dict[str, ConnectedAccount] = {}
    for owner_id in owners:
        if owner_id in _account_cache:
            result[owner_id] = _account_cache[owner_id]
        else:
            result[owner_id] = _provision(owner_id)
    return result


def get_connected_account(owner_id: str) -> ConnectedAccount | None:
    """Return the cached ConnectedAccount for owner_id, or None if not provisioned."""
    return _account_cache.get(owner_id)
