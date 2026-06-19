"""plaid_conn.py — Plaid /transactions/sync connector for NemoClaw.

Exports: PlaidConnector

Uses the cursor-based /transactions/sync endpoint for incremental delta sync.
On first run the cursor is empty and Plaid returns a full history page.
The returned next_cursor is persisted in state so subsequent runs only fetch
what changed since the last call.

Environment variables (read at fetch time, never at import):
  PLAID_CLIENT_ID  — Plaid dashboard client ID
  PLAID_SECRET     — environment-specific secret
  PLAID_ACCESS_TOKEN — per-bank access token obtained via Plaid Link
  PLAID_ENV        — "sandbox" | "production" (default "sandbox")

Sign convention:
  Plaid `amount` is POSITIVE for outflows (debits/expenses) and NEGATIVE for
  credits (refunds, income deposits). We invert to our schema where `amount`
  is always a positive float and `direction` is "expense"|"income".

  #COMPLETION_DRIVE: Plaid sign convention verified against
  https://plaid.com/docs/api/products/transactions/#transactionssync
  (positive = debit/expense, negative = credit/income).
  #SUGGEST_VERIFY: run against Plaid sandbox with a test access token and
  confirm that a known deposit appears as direction="income" in the output.

Failed import or missing env vars raise ConnectorError so the loop can
skip and report rather than crash the full cycle.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from connectors.base import ConnectorError

if TYPE_CHECKING:
    from agent.tenancy import Tenant

_PLAID_ENVS = {
    "sandbox": "https://sandbox.plaid.com",
    "production": "https://production.plaid.com",
}


def _plaid_env_url() -> str:
    """Return the Plaid base URL for the configured PLAID_ENV."""
    env = os.environ.get("PLAID_ENV", "sandbox").lower()
    return _PLAID_ENVS.get(env, _PLAID_ENVS["sandbox"])


def _map_transaction(raw: Any) -> dict[str, Any]:
    """Map a single Plaid transaction object to the normalized schema.

    Plaid sign: positive amount = debit (expense), negative = credit (income).
    We store amount as an absolute float and set direction accordingly.

    #COMPLETION_DRIVE: Plaid personal_finance_category.primary used for category
    when available; falls back to raw category[0] then "Other".
    #SUGGEST_VERIFY: compare category mapping against Plaid sandbox fixture before
    using in production to confirm the attribute path is correct for SDK v18+.
    """
    raw_amount = float(getattr(raw, "amount", 0.0))
    direction = "expense" if raw_amount >= 0 else "income"
    amount = abs(raw_amount)

    date_val = getattr(raw, "date", None) or getattr(raw, "authorized_date", None)
    if hasattr(date_val, "isoformat"):
        date_str = date_val.isoformat()
    else:
        date_str = str(date_val or "")

    vendor = (
        getattr(raw, "merchant_name", None)
        or getattr(raw, "name", None)
        or "Unknown"
    )

    pfc = getattr(raw, "personal_finance_category", None)
    if pfc is not None:
        category = getattr(pfc, "primary", None) or "Other"
    else:
        cats = getattr(raw, "category", None) or []
        category = cats[0] if cats else "Other"

    return {
        "date": date_str,
        "vendor": str(vendor),
        "amount": amount,
        "direction": direction,
        "category": str(category),
        "source": f"plaid:{getattr(raw, 'transaction_id', 'unknown')}",
    }


def _build_plaid_client() -> Any:
    """Build and return a configured plaid.ApiClient.

    Raises ConnectorError if plaid-python is not installed or env vars are missing.
    Lazy import keeps the core module importable without the optional dep.
    """
    try:
        import plaid  # noqa: F401 — availability check
        from plaid.api import plaid_api
        from plaid.model.products import Products  # noqa: F401
        import plaid.configuration as plaid_config
    except ImportError as exc:
        raise ConnectorError(
            "plaid-python is not installed. "
            "Install with: pip install 'nemoclaw-smb[plaid]'"
        ) from exc

    client_id = os.environ.get("PLAID_CLIENT_ID", "")
    secret = os.environ.get("PLAID_SECRET", "")
    if not client_id or not secret:
        raise ConnectorError(
            "PLAID_CLIENT_ID and PLAID_SECRET must be set in the tenant environment."
        )

    base_url = _plaid_env_url()
    configuration = plaid_config.Configuration(
        host=base_url,
        api_key={"clientId": client_id, "secret": secret},
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def _sync_page(client: Any, access_token: str, cursor: str) -> tuple[list[Any], str, bool]:
    """Fetch one page from /transactions/sync.

    Returns (added_transactions, next_cursor, has_more).
    Raises ConnectorError wrapping any Plaid API error.
    #COMPLETION_DRIVE: /transactions/sync returns added/modified/removed lists;
    we only consume `added` — modifications and removals are noted but not applied
    to the local dataset in this implementation.
    #SUGGEST_VERIFY: confirm modified/removed handling requirements with the
    product owner before production rollout.
    """
    try:
        from plaid.model.transactions_sync_request import TransactionsSyncRequest

        req = TransactionsSyncRequest(
            access_token=access_token,
            cursor=cursor if cursor else None,
            count=500,
        )
        resp = client.transactions_sync(req)
        added = list(resp.added or [])
        next_cursor = resp.next_cursor or cursor
        has_more = bool(getattr(resp, "has_more", False))
        return added, next_cursor, has_more
    except Exception as exc:
        raise ConnectorError(f"Plaid transactions_sync failed: {exc}") from exc


class PlaidConnector:
    """Connector using Plaid /transactions/sync for cursor-based incremental sync.

    State schema: {"cursor": "<plaid_next_cursor>"}
    On first run cursor is empty; Plaid returns full history.
    cursor is advanced and persisted so subsequent runs only fetch deltas.
    """

    def fetch(
        self,
        tenant: "Tenant",
        state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch new transactions from Plaid since the last cursor position.

        Paginates until has_more is False. Maps each raw transaction to the
        normalized schema. Returns all added transactions + updated state.
        """
        access_token = os.environ.get("PLAID_ACCESS_TOKEN", "")
        if not access_token:
            raise ConnectorError(
                "PLAID_ACCESS_TOKEN must be set in the tenant environment."
            )

        client = _build_plaid_client()
        cursor = state.get("cursor", "")

        all_added: list[dict[str, Any]] = []
        has_more = True
        max_pages = 20  # upper bound to prevent unbounded loops
        pages = 0

        while has_more and pages < max_pages:
            added, cursor, has_more = _sync_page(client, access_token, cursor)
            all_added.extend(_map_transaction(tx) for tx in added)
            pages += 1

        updated_state = {**state, "cursor": cursor}
        return all_added, updated_state
