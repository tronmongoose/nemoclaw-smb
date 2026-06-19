"""spreadsheet.py — Configurable adapter for user-maintained CSV/XLSX files.

Column mapping is read from tenant config under ingestion.spreadsheet.columns:
    date: "Date"            # column header name for transaction date
    vendor: "Vendor"        # column header name for vendor/description
    amount: "Amount"        # column header name for amount
    category: "Category"    # (optional) column header for category
    direction: "Type"       # (optional) "expense"/"income" column; if absent,
                            # derive from amount sign (negative=expense)

#SUGGEST_VERIFY: if column names are not provided in tenant config, we infer
from common header names (see _INFER_MAP). Check the printed mapping before
trusting results on a new file.

Exports: parse_spreadsheet
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

# Common header names mapped to canonical field keys.
# First match wins for each canonical field.
_INFER_MAP: dict[str, list[str]] = {
    "date": ["date", "transaction date", "trans date", "txn date", "posted date", "post date"],
    "vendor": ["vendor", "description", "payee", "merchant", "name"],
    "amount": ["amount", "amount_usd", "price", "total", "debit", "charge"],
    "category": ["category", "type", "label", "tag"],
    "direction": ["direction", "dr/cr", "debit/credit", "flow"],
}


def _resolve_columns(file_headers: list[str], column_map: dict[str, str]) -> dict[str, str | None]:
    """Resolve canonical field -> actual header from explicit map or inferred names.

    Returns dict with keys: date, vendor, amount, category, direction.
    Values are the matching actual header string, or None if not found.
    """
    lower_headers = {h.lower(): h for h in file_headers}
    resolved: dict[str, str | None] = {}

    for canonical, infer_candidates in _INFER_MAP.items():
        explicit = column_map.get(canonical, "")
        if explicit and explicit in file_headers:
            resolved[canonical] = explicit
            continue
        # Infer
        match = next(
            (lower_headers[c] for c in infer_candidates if c in lower_headers),
            None,
        )
        resolved[canonical] = match
        if match is None and canonical in ("date", "vendor", "amount"):
            # Required fields only
            import logging
            logging.getLogger(__name__).warning(
                "spreadsheet: could not resolve required column %r — mapping may be incomplete. "
                "#SUGGEST_VERIFY: add ingestion.spreadsheet.columns.%s to tenant config.",
                canonical, canonical,
            )

    return resolved


def _parse_amount_and_direction(
    amount_str: str,
    direction_str: str | None,
) -> tuple[float, str]:
    """Return (positive_amount, 'expense'|'income') from raw cell values."""
    clean = amount_str.replace("$", "").replace(",", "").strip()
    try:
        raw = float(clean)
    except ValueError:
        raw = 0.0

    if direction_str:
        direction_lower = direction_str.lower().strip()
        if direction_lower in ("expense", "debit", "dr", "charge", "out"):
            return abs(raw), "expense"
        if direction_lower in ("income", "credit", "cr", "payment", "in", "deposit"):
            return abs(raw), "income"

    # Derive from sign: negative = expense (matches Chase and most bank exports)
    if raw < 0:
        return abs(raw), "expense"
    return raw, "income"


def _read_rows_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Return (headers, rows) for a CSV file."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    return headers, list(reader)


def _read_rows_xlsx(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Return (headers, rows) for an XLSX file using openpyxl."""
    import openpyxl  # noqa: PLC0415 — optional dep; only loaded for xlsx
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(c) if c is not None else "" for c in rows[0]]
    data_rows: list[dict[str, str]] = []
    for row in rows[1:]:
        data_rows.append({
            headers[i]: (str(v) if v is not None else "")
            for i, v in enumerate(row)
            if i < len(headers)
        })
    return headers, data_rows


def parse_spreadsheet(path: Path, column_map: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Parse a CSV or XLSX file into normalized transaction dicts.

    column_map: explicit {canonical_field: actual_header} from tenant config.
    Falls back to inferred header names with a logged warning when absent.

    Normalized schema: date, vendor, amount, direction, category, source.
    """
    from gbrain.invoice_ingestion import _parse_date_iso

    col_map = column_map or {}
    suffix = path.suffix.lower()

    if suffix == ".xlsx":
        headers, rows = _read_rows_xlsx(path)
    else:
        headers, rows = _read_rows_csv(path)

    resolved = _resolve_columns(headers, col_map)

    results: list[dict[str, Any]] = []
    for row in rows:
        date_raw = row.get(resolved["date"] or "", "") if resolved["date"] else ""
        vendor_raw = row.get(resolved["vendor"] or "", "") if resolved["vendor"] else "Unknown"
        amount_raw = row.get(resolved["amount"] or "", "0") if resolved["amount"] else "0"
        category_raw = (
            row.get(resolved["category"] or "", "") if resolved["category"] else ""
        )
        direction_raw = (
            row.get(resolved["direction"] or "", "") if resolved["direction"] else None
        )

        date = _parse_date_iso(date_raw.strip())
        vendor = vendor_raw.strip() or "Unknown"
        amount, direction = _parse_amount_and_direction(amount_raw, direction_raw)
        category = category_raw.strip() or None

        results.append({
            "date": date,
            "vendor": vendor,
            "amount": amount,
            "direction": direction,
            "category": category,
            "source": f"spreadsheet:{path.name}",
        })

    return results
