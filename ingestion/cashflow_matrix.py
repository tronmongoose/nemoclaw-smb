"""cashflow_matrix.py — Adapter for category-by-month cashflow matrix CSVs (STR P&L).

A cashflow matrix has month tokens in its header row (jan/feb/.../dec) and
category labels in column 0, with dollar amounts in the interior cells.
It is distinct from a Chase transaction CSV and from a row-per-transaction spreadsheet.

Exports: is_matrix, load_matrix, DEFAULT_INCOME, DEFAULT_EXPENSE, DEFAULT_SKIP
"""

from __future__ import annotations

import calendar
import csv
import io
import re
from pathlib import Path
from typing import Any

_MONTH_TOKENS = {
    "jan", "feb", "mar", "march", "apr", "may", "jun", "june",
    "jul", "july", "aug", "sept", "sep", "oct", "nov", "dec",
}

_MONTH_INDEX: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "march": 3, "apr": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8,
    "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

DEFAULT_INCOME: list[str] = ["Revenue", "Pet fees", "Parents/Friends Stay"]
DEFAULT_EXPENSE: list[str] = [
    "Mgmt Fees",
    "Yard care X2 a  month",
    "Oceanside Munirevs",
    "Water+water waste (COO)",
    "City Waste (waste mgmt)",
    "Internet (7962)",
    "Electricity+ Gas (SDGE)",
    "Instacart+Amazon",
    "Owner Exp (extra)",
]
DEFAULT_SKIP: list[str] = [
    "", "Net to owner", "Notes", "Total",
    "Avg Total Proceeds/Month", "Months",
]


def _normalize_label(label: str) -> str:
    """Collapse extra whitespace and lowercase for case-insensitive matching."""
    return re.sub(r"\s+", " ", label).strip().lower()


def _build_lookup(labels: list[str]) -> set[str]:
    """Return a set of normalized labels for O(1) membership checks."""
    return {_normalize_label(lb) for lb in labels}


def is_matrix(path: Path) -> bool:
    """Return True when the file's header row contains month tokens.

    Distinguishes a cashflow matrix (month headers) from a Chase CSV
    (which has "transaction date" in its header) and generic spreadsheets.
    """
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        header = next(reader, None)
        if header is None:
            return False
        tokens = {cell.strip().lower() for cell in header if cell.strip()}
        return bool(tokens & _MONTH_TOKENS)
    except Exception:  # noqa: BLE001
        return False


def _infer_year(path: Path) -> int | None:
    """Infer a 4-digit year from trailing digits in the filename stem.

    #COMPLETION_DRIVE: 2-digit suffix "25" -> 2025; 4-digit match takes priority.
    #SUGGEST_VERIFY: confirm this heuristic against your filename conventions.
    """
    stem = path.stem
    four = re.search(r"(20\d{2})", stem)
    if four:
        return int(four.group(1))
    two = re.search(r"(\d{2})$", stem)
    if two:
        suffix = int(two.group(1))
        return 2000 + suffix if suffix <= 99 else None
    return None


def _parse_amount(cell: str) -> float | None:
    """Parse a dollar-amount cell; return None for blank or non-numeric entries.

    Handles: "$1,234.56", "(123.45)" for negatives, blank, "-".
    """
    s = cell.strip()
    if not s or s == "-":
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace("$", "").replace(",", "").strip()
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def _last_day(year: int, month: int) -> str:
    """Return ISO date string for the last day of year/month."""
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last:02d}"


def _find_month_columns(header: list[str]) -> list[tuple[int, int]]:
    """Return [(col_index, month_number), ...] for the 12 calendar month columns.

    #COMPLETION_DRIVE: stops at Total/projection columns by taking only columns
    whose header token is a recognized month name; unrecognized labels (Total,
    Projected Summer Low, blanks) are silently skipped.
    #SUGGEST_VERIFY: check against matrices that list months in non-standard order.
    """
    result: list[tuple[int, int]] = []
    for idx, cell in enumerate(header):
        token = cell.strip().lower()
        month_num = _MONTH_INDEX.get(token)
        if month_num is not None:
            result.append((idx, month_num))
    return result


def load_matrix(
    path: Path,
    year: int | None,
    income: list[str],
    expense: list[str],
    skip: list[str],
) -> list[dict[str, Any]]:
    """Parse a cashflow matrix CSV into normalized transaction dicts.

    For each non-skip category row and each month column with a parseable amount,
    emits one record per cell:
        date (ISO last day of month), vendor (category label), amount (abs float),
        direction ("income"|"expense"), category (category label), source "cashflow"

    year: use tenant config value; if None, infer from filename or fall back to
    calendar.datetime.today().year.
    """
    import datetime

    if year is None:
        year = _infer_year(path) or datetime.date.today().year

    income_set = _build_lookup(income)
    expense_set = _build_lookup(expense)
    skip_set = _build_lookup(skip)

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    month_cols = _find_month_columns(header)

    records: list[dict[str, Any]] = []
    for row in reader:
        if not row:
            continue
        label = row[0].strip()
        norm = _normalize_label(label)

        if norm in skip_set or norm == "":
            continue

        if norm in income_set:
            direction = "income"
        elif norm in expense_set:
            direction = "expense"
        else:
            continue  # unrecognized row — not income, expense, or skip

        for col_idx, month_num in month_cols:
            cell = row[col_idx] if col_idx < len(row) else ""
            amount = _parse_amount(cell)
            if amount is None:
                continue
            records.append({
                "date": _last_day(year, month_num),
                "vendor": label,
                "amount": abs(amount),
                "direction": direction,
                "category": label,
                "source": "cashflow",
            })

    return records
