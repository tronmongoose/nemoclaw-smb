"""chase_csv.py — Adapter for Chase credit-card CSV export.

Chase CSV header (canonical):
    Transaction Date, Post Date, Description, Category, Type, Amount, Memo

Sign convention: Chase encodes charges as NEGATIVE amounts and payments/credits
as POSITIVE amounts. We invert: a negative Amount becomes a positive expense,
a positive Amount becomes a positive income (credit/payment).

#COMPLETION_DRIVE: Chase Type field values include "Sale" (charge) and
"Payment" (credit); we derive direction from Amount sign so Type is not required.
#SUGGEST_VERIFY: export a real Chase CSV and confirm the Amount column sign
before running against production data.

Exports: is_chase_csv, parse_chase_csv
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

_CHASE_REQUIRED_HEADERS = {
    "transaction date",
    "post date",
    "description",
    "category",
    "type",
    "amount",
}


def is_chase_csv(path: Path) -> bool:
    """Return True when the file's first row matches the Chase credit-card header."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            return False
        headers = {h.strip().lower() for h in reader.fieldnames if h}
        return _CHASE_REQUIRED_HEADERS.issubset(headers)
    except Exception:  # noqa: BLE001
        return False


def parse_chase_csv(path: Path) -> list[dict[str, Any]]:
    """Parse a Chase credit-card CSV into normalized transaction dicts.

    Normalized schema:
        date (ISO YYYY-MM-DD), vendor (str), amount (float, always positive),
        direction ("expense"|"income"), category (str|None), source (str)

    A Chase charge (negative Amount) maps to direction="expense".
    A Chase payment or credit (positive Amount) maps to direction="income".
    """
    from gbrain.invoice_ingestion import _parse_date_iso  # reuse existing helper

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    # Normalize header keys once
    def _norm(row: dict) -> dict:
        return {k.strip().lower(): v.strip() if isinstance(v, str) else v for k, v in row.items()}

    results: list[dict[str, Any]] = []
    for raw_row in reader:
        row = _norm(raw_row)
        date_str = row.get("transaction date", "") or row.get("post date", "")
        date = _parse_date_iso(date_str)
        description = row.get("description", "").strip()
        category = row.get("category", "").strip() or None
        memo = row.get("memo", "").strip()

        raw_amount_str = row.get("amount", "0").replace("$", "").replace(",", "").strip()
        try:
            raw_amount = float(raw_amount_str)
        except ValueError:
            raw_amount = 0.0

        # Chase: negative = charge/expense, positive = payment/credit
        if raw_amount < 0:
            direction = "expense"
            amount = abs(raw_amount)
        else:
            direction = "income"
            amount = raw_amount

        vendor = description or memo or "Unknown"

        results.append({
            "date": date,
            "vendor": vendor,
            "amount": amount,
            "direction": direction,
            "category": category,
            "source": f"chase:{path.name}",
        })

    return results
