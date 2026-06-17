"""
invoice_ingestion.py — SMB vendor invoice parsing, normalization, recurring detection, and GBrain record production.

Exports:
    Invoice              — dataclass for a normalized invoice record
    parse_invoice        — normalize one raw invoice dict to Invoice
    normalize_vendor     — clean a raw description string to a canonical vendor name
    categorize_vendor    — map vendor name to SMB category string
    detect_recurring     — group invoices by vendor, detect 2+ charges at regular intervals
    ingest_to_graph_records — produce GBrain-ready node/edge dicts (anomaly_flag placeholder only)
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# SMB vendor → category map
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, str] = {
    # Design/Creative
    "adobe": "Design/Creative",
    "figma": "Design/Creative",
    "canva": "Design/Creative",
    # Cloud/Infra
    "aws": "Cloud/Infra",
    "amazon web services": "Cloud/Infra",
    "gcp": "Cloud/Infra",
    "google cloud": "Cloud/Infra",
    "azure": "Cloud/Infra",
    "vercel": "Cloud/Infra",
    "cloudflare": "Cloud/Infra",
    "digitalocean": "Cloud/Infra",
    "digital ocean": "Cloud/Infra",
    "heroku": "Cloud/Infra",
    "namecheap": "Cloud/Infra",
    # Payroll/HR
    "gusto": "Payroll/HR",
    "rippling": "Payroll/HR",
    "deel": "Payroll/HR",
    "remote.com": "Payroll/HR",
    # Productivity
    "slack": "Productivity",
    "notion": "Productivity",
    "google workspace": "Productivity",
    "microsoft 365": "Productivity",
    "zoom": "Productivity",
    "dropbox": "Productivity",
    "1password": "Productivity",
    "linear": "Productivity",
    "github": "Productivity",
    "jira": "Productivity",
    "confluence": "Productivity",
    "airtable": "Productivity",
    "loom": "Productivity",
    "intercom": "Productivity",
}

# Interval windows (days) — same heuristics as subscription_import.py source
_MONTHLY_MIN, _MONTHLY_MAX = 20, 40
_QUARTERLY_MIN, _QUARTERLY_MAX = 80, 100
_ANNUAL_MIN, _ANNUAL_MAX = 340, 400

# Amount-similarity tolerance: 15% band
_AMOUNT_TOLERANCE = 0.15


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class Invoice:
    """Normalized representation of a single vendor invoice."""

    vendor: str
    amount: float
    date: str           # ISO 8601: YYYY-MM-DD
    category: str
    raw_description: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_vendor(description: str) -> str:
    """Return a canonical lowercase vendor name stripped of transaction noise."""
    desc = description.lower().strip()
    for prefix in ["pos ", "ach ", "recurring ", "autopay ", "debit ", "purchase ",
                   "checkcard ", "visa ", "mastercard ", "sq *", "paypal *", "inv#",
                   "invoice "]:
        if desc.startswith(prefix):
            desc = desc[len(prefix):]
    # Drop trailing ref numbers, dates, state abbreviations, store numbers
    desc = re.sub(r'\s+\d{4,}.*$', '', desc)
    desc = re.sub(r'\s+\d{2}/\d{2}.*$', '', desc)
    desc = re.sub(r'\s+#\d+.*$', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc


def categorize_vendor(vendor: str) -> str:
    """Map a vendor name to an SMB category; returns 'Other' on no match."""
    vendor_lower = vendor.lower()
    for keyword, category in _CATEGORY_MAP.items():
        if keyword in vendor_lower:
            return category
    return "Other"


def parse_invoice(raw: dict) -> Invoice:
    """Normalize one raw invoice dict to an Invoice dataclass.

    Expected keys: description (str), amount (str | float), date (str).
    Optional key: category (str) — overrides categorize_vendor when supplied.
    """
    raw_description = str(raw.get("description", "")).strip()
    vendor = normalize_vendor(raw_description)

    amount_raw = raw.get("amount", 0)
    if isinstance(amount_raw, str):
        amount = _parse_amount(amount_raw)
    else:
        amount = float(amount_raw)

    date_raw = str(raw.get("date", "")).strip()
    date = _parse_date_iso(date_raw)

    #COMPLETION_DRIVE: if caller supplies "category", trust it; otherwise derive
    category = str(raw.get("category", "")).strip() or categorize_vendor(vendor)

    return Invoice(
        vendor=vendor,
        amount=abs(amount),
        date=date,
        category=category,
        raw_description=raw_description,
    )


def detect_recurring(invoices: list[dict]) -> list[dict]:
    """Group invoices by normalized vendor; return vendors with 2+ charges at regular intervals.

    Each returned dict: {vendor, amount, frequency, monthly_cost, last_seen (ISO str), occurrences}.
    Interval heuristics: monthly 20-40d, quarterly 80-100d, annual 340-400d.
    """
    by_vendor: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in invoices:
        inv = parse_invoice(raw)
        by_vendor[inv.vendor].append({
            "date": datetime.fromisoformat(inv.date),
            "amount": inv.amount,
            "category": inv.category,
        })

    results: list[dict] = []
    for vendor, entries in by_vendor.items():
        if len(entries) < 2:
            continue
        found = _find_recurring_group(vendor, entries)
        if found:
            results.append(found)

    results.sort(key=lambda x: x["monthly_cost"], reverse=True)
    return results


def ingest_to_graph_records(invoices: list[dict]) -> list[dict]:
    """Produce GBrain-ready node/edge dicts from a list of raw invoice dicts.

    For each unique vendor: one vendor node.
    For each invoice: one 'paid' edge from a synthetic 'company' node to the vendor node.
    anomaly_flag is None — anomaly scoring is a separate module.
    """
    records: list[dict] = []
    seen_vendors: set[str] = set()

    for raw in invoices:
        inv = parse_invoice(raw)

        if inv.vendor not in seen_vendors:
            records.append({
                "record_type": "node",
                "node_type": "vendor",
                "id": f"vendor:{inv.vendor}",
                "label": inv.vendor,
                "category": inv.category,
            })
            seen_vendors.add(inv.vendor)

        records.append({
            "record_type": "edge",
            "edge_type": "paid",
            "source": "company:self",
            "target": f"vendor:{inv.vendor}",
            "amount": inv.amount,
            "date": inv.date,
            "category": inv.category,
            "raw_description": inv.raw_description,
            "anomaly_flag": None,
        })

    return records


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_amount(amount_str: str) -> float:
    """Parse dollar amount string, handling symbols and parenthetical negatives."""
    s = amount_str.strip().replace("$", "").replace(",", "")
    if not s or s == "--":
        return 0.0
    if s.startswith("(") and s.endswith(")"):
        return -float(s[1:-1])
    return float(s)


def _parse_date_iso(date_str: str) -> str:
    """Parse various date formats and return ISO 8601 YYYY-MM-DD string."""
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%Y/%m/%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    #COMPLETION_DRIVE: unparseable dates become today to avoid hard failures at the boundary
    return datetime.now().strftime("%Y-%m-%d")


def _find_recurring_group(vendor: str, entries: list[dict[str, Any]]) -> dict | None:
    """Return a recurring summary dict for a vendor group, or None if no regular interval found."""
    amount_groups: defaultdict[float, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        amount = entry["amount"]
        matched = False
        for key in list(amount_groups.keys()):
            if abs(amount - key) / max(key, 0.01) < _AMOUNT_TOLERANCE:
                amount_groups[key].append(entry)
                matched = True
                break
        if not matched:
            amount_groups[amount].append(entry)

    for _key, group in amount_groups.items():
        if len(group) < 2:
            continue
        dates = sorted(e["date"] for e in group)
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_interval = sum(intervals) / len(intervals)

        if _MONTHLY_MIN <= avg_interval <= _MONTHLY_MAX:
            frequency = "monthly"
            divisor = 1
        elif _QUARTERLY_MIN <= avg_interval <= _QUARTERLY_MAX:
            frequency = "quarterly"
            divisor = 3
        elif _ANNUAL_MIN <= avg_interval <= _ANNUAL_MAX:
            frequency = "annual"
            divisor = 12
        else:
            continue

        amounts = [e["amount"] for e in group]
        avg_cost = sum(amounts) / len(amounts)
        latest = max(group, key=lambda e: e["date"])

        return {
            "vendor": vendor,
            "amount": round(avg_cost, 2),
            "frequency": frequency,
            "monthly_cost": round(avg_cost / divisor, 2),
            "last_seen": latest["date"].strftime("%Y-%m-%d"),
            "occurrences": len(group),
        }

    return None
