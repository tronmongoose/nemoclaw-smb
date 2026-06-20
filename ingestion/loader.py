"""loader.py — File discovery and transaction loading for a tenant.

Exports: load_transactions

Discovers *.csv and *.xlsx files in tenant.data_root, dispatches each to
the appropriate adapter:
  - cashflow matrix (month headers detected by is_matrix) -> cashflow_matrix adapter
  - Chase CSV (Chase header detected by is_chase_csv) -> chase_csv adapter
  - all others -> spreadsheet adapter with column map from tenant config

When ingestion.include globs are present in tenant config, only files matching
at least one glob are ingested. This lets a tenant select just the cashflow
matrix CSV and exclude a Chase CSV to avoid double-counting the same spend.

Merges results, deduplicates by (date, vendor, amount), and sorts by date.
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


def _get_include_globs(tenant: "Tenant") -> list[str]:
    """Extract ingestion.include glob list from tenant config; empty means include all."""
    ingestion = getattr(tenant, "ingestion", {}) or {}
    if not isinstance(ingestion, dict):
        return []
    include = ingestion.get("include")
    if not include:
        return []
    return list(include) if isinstance(include, (list, tuple)) else [str(include)]


def _get_cashflow_config(tenant: "Tenant") -> dict[str, Any]:
    """Extract ingestion.cashflow sub-config from tenant config."""
    ingestion = getattr(tenant, "ingestion", {}) or {}
    if not isinstance(ingestion, dict):
        return {}
    cashflow = ingestion.get("cashflow")
    return dict(cashflow) if isinstance(cashflow, dict) else {}


def _file_matches_include(path: Path, globs: list[str]) -> bool:
    """Return True when the file matches any of the provided glob patterns."""
    for pattern in globs:
        if path.match(pattern):
            return True
    return False


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

    Dispatch order: cashflow_matrix -> chase_csv -> spreadsheet.
    """
    from ingestion.cashflow_matrix import (
        DEFAULT_EXPENSE, DEFAULT_INCOME, DEFAULT_SKIP, is_matrix, load_matrix,
    )
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

    include_globs = _get_include_globs(tenant)
    if include_globs:
        files = [f for f in files if _file_matches_include(f, include_globs)]
        if not files:
            _log.warning(
                "load_transactions: include globs %s matched no files in %s",
                include_globs, data_root,
            )
            return []

    col_map = _get_column_map(tenant)
    cf_cfg = _get_cashflow_config(tenant)
    cf_year: int | None = cf_cfg.get("year") or None
    cf_income: list[str] = cf_cfg.get("income", DEFAULT_INCOME)
    cf_expense: list[str] = cf_cfg.get("expense", DEFAULT_EXPENSE)
    cf_skip: list[str] = cf_cfg.get("skip", DEFAULT_SKIP)

    all_transactions: list[dict[str, Any]] = []
    for f in files:
        try:
            if is_matrix(f):
                txns = load_matrix(f, cf_year, cf_income, cf_expense, cf_skip)
                _log.info(
                    "load_transactions: %s -> cashflow_matrix adapter (%d rows)",
                    f.name, len(txns),
                )
            elif is_chase_csv(f):
                txns = parse_chase_csv(f)
                _log.info(
                    "load_transactions: %s -> chase adapter (%d rows)",
                    f.name, len(txns),
                )
            else:
                txns = parse_spreadsheet(f, column_map=col_map)
                _log.info(
                    "load_transactions: %s -> spreadsheet adapter (%d rows)",
                    f.name, len(txns),
                )
            all_transactions.extend(txns)
        except Exception as exc:  # noqa: BLE001
            _log.warning("load_transactions: failed to parse %s: %s", f.name, exc)

    deduped = _dedup(all_transactions)
    deduped.sort(key=lambda t: t.get("date", ""))
    return deduped
