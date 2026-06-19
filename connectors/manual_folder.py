"""manual_folder.py — Connector that wraps the existing ingestion/loader.

Exports: ManualFolderConnector

Reads all CSV/XLSX files dropped in tenant.data_root via the existing loader.
Deduplication happens downstream in the loader itself, so re-ingesting overlapping
periods is safe.  State is a no-op ({}) — the loader has no incremental cursor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.tenancy import Tenant


class ManualFolderConnector:
    """Connector backed by files dropped in tenant.data_root.

    Delegates entirely to ingestion.loader.load_transactions.
    State is always returned unchanged; this connector has no cursor.
    """

    def fetch(
        self,
        tenant: "Tenant",
        state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return all transactions found on disk + the unchanged state dict."""
        from ingestion.loader import load_transactions

        transactions = load_transactions(tenant)
        return transactions, state
