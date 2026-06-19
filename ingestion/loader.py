"""loader.py — File discovery and transaction loading for a tenant.

Exports: load_transactions

Discovers *.csv and *.xlsx files in tenant.data_root, dispatches each to
the appropriate adapter (Chase CSV if Chase header detected, else spreadsheet),
merges results, deduplicates by (date, vendor, amount), and sorts by date.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.tenancy import Tenant

_log = logging.getLogger(__name__)

_SUPPORTED_GLOB_PATTERNS = ["*.csv", "*.xlsx"]


def _get_column_map(tenant: "Tenant") -> dict[str, str]:
    """Extract ingestion.spreadsheet.columns from tenant.ingestion, if present."""
    ingestion = getattr(tenant, "ingestion", {}) or {}
    spreadsheet = ingestion.get("spreadsheet", {}) if isinstance(ingestion, dict) else {}
    return spreadsheet.get("columns", {}) if isinstance(spreadsheet, dict) else {}


def _dedup(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by (date, vendor, amount); preserve first occurrence order."""
    seen: set[tuple] = set()
    result: list[dict[str, Any]] = []
    for tx in transactions:
        key = (tx.get("date"), tx.get("vendor"), tx.get("amount"))
        if key not in seen:
            seen.add(key)
            result.append(tx)
    return result


def load_transactions(tenant: "Tenant") -> list[dict[str, Any]]:
    """Discover, parse, deduplicate, and sort transactions from tenant.data_root.

    Returns a list of normalized dicts:
        date (ISO), vendor (str), amount (float, positive),
        direction ("expense"|"income"), category (str|None), source (str)

    Files matching Chase CSV header use chase_csv adapter; all others use
    spreadsheet adapter with column map from tenant config.
    """
    from ingestion.chase_csv import is_chase_csv, parse_chase_csv
    from ingestion.spreadsheet import parse_spreadsheet

    data_root = Path(tenant.data_root)
    if not data_root.exists():
        _log.warning("load_transactions: data_root does not exist: %s", data_root)
        return []

    files: list[Path] = []
    for pattern in _SUPPORTED_GLOB_PATTERNS:
        files.extend(sorted(data_root.glob(pattern)))

    if not files:
        _log.warning("load_transactions: no CSV/XLSX files found in %s", data_root)
        return []

    # Column map only used by spreadsheet adapter; lazily resolved once.
    col_map = _get_column_map(tenant)

    all_transactions: list[dict[str, Any]] = []
    for f in files:
        try:
            if is_chase_csv(f):
                txns = parse_chase_csv(f)
                _log.info("load_transactions: %s -> chase adapter (%d rows)", f.name, len(txns))
            else:
                txns = parse_spreadsheet(f, column_map=col_map)
                _log.info("load_transactions: %s -> spreadsheet adapter (%d rows)", f.name, len(txns))
            all_transactions.extend(txns)
        except Exception as exc:  # noqa: BLE001
            _log.warning("load_transactions: failed to parse %s: %s", f.name, exc)

    deduped = _dedup(all_transactions)
    deduped.sort(key=lambda t: t.get("date", ""))
    return deduped
