"""
NemoClaw Intuit QuickBooks reconciler — sandbox/mock ledger interface.

Behavior: if INTUIT_CLIENT_ID + INTUIT_CLIENT_SECRET are present in env AND
the intuit-oauth SDK is importable, a live sandbox path could be wired; today
only the deterministic mock path ships. Default is always sandbox/mock.

Public API:
    reconcile(payment, category=None, date=None) -> dict
    ledger() -> list[dict]
"""

import hashlib
import json
import os
from datetime import date as _date_type
from datetime import datetime
from typing import Optional, Union

# #GLOBAL-STATE: demo ledger accumulator — module-level list, fine for demo scope.
_LEDGER: list[dict] = []

# #COMPLETION_DRIVE: credential detection is structural scaffolding;
# live Intuit SDK path intentionally unimplemented for demo safety.
_INTUIT_READY = bool(
    os.environ.get("INTUIT_CLIENT_ID") and os.environ.get("INTUIT_CLIENT_SECRET")
)

_DEFAULT_ACCOUNT = "Software/SaaS Expense"

_CATEGORY_ACCOUNT_MAP = {
    "saas": "Software/SaaS Expense",
    "software": "Software/SaaS Expense",
    "cloud": "Cloud Infrastructure",
    "payroll": "Payroll Expense",
    "marketing": "Marketing & Advertising",
    "travel": "Travel & Entertainment",
    "utilities": "Utilities",
}


def _entry_id(payment: dict, txn_date: str) -> str:
    """Derive a stable entry ID from the payment dict and date."""
    raw = json.dumps({"id": payment.get("id"), "date": txn_date}, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"qb_sandbox_{digest}"


def _resolve_account(category: Optional[str]) -> str:
    """Map an optional category string to a QuickBooks account name."""
    if not category:
        return _DEFAULT_ACCOUNT
    key = category.lower().strip()
    for fragment, account in _CATEGORY_ACCOUNT_MAP.items():
        if fragment in key:
            return account
    return _DEFAULT_ACCOUNT


def reconcile(
    payment: dict,
    category: Optional[str] = None,
    date: Optional[Union[str, _date_type]] = None,
) -> dict:
    """Post a stripe pay() result as a QuickBooks-style ledger entry."""
    if isinstance(date, _date_type):
        txn_date = date.isoformat()
    elif date:
        txn_date = str(date)
    else:
        txn_date = datetime.utcnow().date().isoformat()

    entry = {
        "entry_id": _entry_id(payment, txn_date),
        "account": _resolve_account(category),
        "vendor": payment.get("vendor", "unknown"),
        "amount": payment.get("amount"),
        "txn_date": txn_date,
        "source": "stripe",
        "status": "posted",
        "mode": "sandbox",
    }
    _LEDGER.append(entry)
    return entry


def ledger() -> list[dict]:
    """Return all reconciled entries accumulated this process."""
    return list(_LEDGER)
