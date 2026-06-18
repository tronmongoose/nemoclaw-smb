"""
seed_data.py — Demo seed data for nemoclaw-smb (Pinwheel Studio, 12-person design studio).

Exports:
    studio_profile      — static studio metadata dict
    seed_invoices       — 5-month invoice history (Jan-May 2026) + June anomaly entry
    aws_renewal_402     — normal AWS renewal that should auto-pay silently
    adobe_anomaly_402   — Adobe $340 spike event that should flag
    affinity_alternative — cheaper Affinity Suite procurement option
"""

from __future__ import annotations

import itertools
from datetime import date

# ---------------------------------------------------------------------------
# Studio profile
# ---------------------------------------------------------------------------

def studio_profile() -> dict:
    """Return static metadata for the demo client (Pinwheel Studio)."""
    return {
        "name": "Pinwheel Studio",
        "headcount": 12,
        "type": "design studio",
        "contacts": [
            {"name": "Marisol Vega", "role": "CEO", "email": "marisol@pinwheelstudio.io"},
            {"name": "Dev Patel", "role": "Head of Operations", "email": "dev@pinwheelstudio.io"},
        ],
        "onboarded_via": "CEO conversation",
    }


# ---------------------------------------------------------------------------
# Invoice history constants
# ---------------------------------------------------------------------------

#COMPLETION_DRIVE: amounts vary slightly month-to-month to simulate real billing rounding
_ADOBE_HISTORY = [275.50, 277.00, 276.80, 278.20, 277.40]  # Jan-May, ~277/mo
_ADOBE_ANOMALY = 340.00                                      # June: +23% spike

_FIGMA_AMOUNT = 144.00    # flat
_AWS_AMOUNT   = 312.00    # flat
_GUSTO_AMOUNT = 1200.00   # flat

_MONTHS = [
    (2026,  1, 15),
    (2026,  2, 15),
    (2026,  3, 15),
    (2026,  4, 15),
    (2026,  5, 15),
]

_JUNE = (2026, 6, 15)

_id_counter = itertools.count(1001)


def _inv_id() -> str:
    """Return the next sequential invoice ID string."""
    return f"INV-{next(_id_counter)}"


def _make_invoice(vendor: str, description: str, amount: float,
                  year: int, month: int, day: int, category: str) -> dict:
    """Build one invoice dict compatible with invoice_ingestion and anomaly_detector."""
    return {
        "invoice_id": _inv_id(),
        "vendor": vendor,
        "description": description,
        "amount": amount,
        "date": date(year, month, day).isoformat(),
        "category": category,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def seed_invoices() -> list[dict]:
    """Return 26 invoices: 5 months of Adobe/Figma/AWS/Gusto + June Adobe anomaly."""
    records: list[dict] = []

    for i, (y, m, d) in enumerate(_MONTHS):
        records.append(_make_invoice(
            "Adobe Creative Cloud", "adobe creative cloud subscription",
            _ADOBE_HISTORY[i], y, m, d, "Design/Creative",
        ))
        records.append(_make_invoice(
            "Figma", "figma team plan",
            _FIGMA_AMOUNT, y, m, d, "Design/Creative",
        ))
        records.append(_make_invoice(
            "AWS", "aws monthly usage",
            _AWS_AMOUNT, y, m, d, "Cloud/Infra",
        ))
        records.append(_make_invoice(
            "Gusto", "gusto payroll processing",
            _GUSTO_AMOUNT, y, m, d, "Payroll/HR",
        ))

    # June Adobe anomaly entry (+23%)
    y, m, d = _JUNE
    records.append(_make_invoice(
        "Adobe Creative Cloud", "adobe creative cloud subscription",
        _ADOBE_ANOMALY, y, m, d, "Design/Creative",
    ))

    return records


def aws_renewal_402() -> dict:
    """Return the in-range AWS renewal 402 event — should auto-pay silently."""
    y, m, d = _JUNE
    return {
        "vendor": "AWS",
        "amount": _AWS_AMOUNT,
        "date": date(y, m, d).isoformat(),
        "invoice_id": _inv_id(),
        "trigger": "http_402",
    }


def adobe_anomaly_402() -> dict:
    """Return the Adobe $340 spike 402 event — should flag for human review."""
    y, m, d = _JUNE
    return {
        "vendor": "Adobe Creative Cloud",
        "amount": _ADOBE_ANOMALY,
        "date": date(y, m, d).isoformat(),
        "invoice_id": _inv_id(),
        "trigger": "http_402",
    }


def affinity_alternative() -> dict:
    """Return the Affinity Suite one-time annual option for the procurement scene."""
    return {
        "vendor": "Affinity Suite",
        "amount": 89.0,
        "frequency": "annual",
        "note": "one-time flat vs Adobe monthly",
        "monthly_equivalent": round(89.0 / 12, 2),  # 7.42
    }


def seed_alternatives() -> list[dict]:
    """Return ranked Adobe Creative Cloud alternatives for the savings endpoints.

    Sourced from the scene_3 alternatives in demo_runner (read-only reference).
    """
    return [
        affinity_alternative(),
        {
            "vendor": "Adobe Photography Plan",
            "amount": 120.0,
            "frequency": "monthly",
            "monthly_equivalent": 120.0,
            "note": "reduced Adobe plan; photography + Lightroom only",
        },
    ]
