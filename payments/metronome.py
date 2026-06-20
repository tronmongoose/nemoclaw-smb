"""payments/metronome.py: Usage-based billing via Metronome (mocked).

Calculates monthly owner invoices as a percentage of nightly revenue collected,
with itemized line items per property. All Metronome API calls are mocked.

Public API:
    InvoiceLine: dataclass for a single line item
    OwnerInvoice: dataclass for one owner's monthly invoice
    calculate_ubp(owner_id, month) -> OwnerInvoice
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

from data.mock_ledger import PROPERTIES, MONTHLY_REVENUE, list_properties_for_owner

_logger = logging.getLogger(__name__)

# Management fee percentage billed via Metronome UBP
_PLATFORM_FEE_PCT: float = 0.005  # 0.5% platform fee on collected revenue


@dataclass
class InvoiceLine:
    """One line item in an owner's UBP invoice."""

    property_id: str
    property_name: str
    revenue_cents: int
    fee_pct: float
    fee_cents: int
    description: str


@dataclass
class OwnerInvoice:
    """Monthly usage-based billing invoice for one owner."""

    owner_id: str
    month: str
    invoice_id: str
    line_items: list[InvoiceLine] = field(default_factory=list)
    total_revenue_cents: int = 0
    total_fee_cents: int = 0
    backend: str = "mock"


def _stable_invoice_id(owner_id: str, month: str) -> str:
    """Return a deterministic mock invoice id."""
    raw = json.dumps([owner_id, month], sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"inv_{digest}"


def calculate_ubp(owner_id: str, month: str) -> OwnerInvoice:
    """Calculate the usage-based billing invoice for owner_id for the given month.

    Itemizes one line per property owned. Fee = management_contract_pct of revenue,
    plus the NemoClaw platform fee (0.5%). month should be "YYYY-MM".
    """
    #COMPLETION_DRIVE: live Metronome would ingest events and return an invoice object
    property_ids = list_properties_for_owner(owner_id)
    invoice = OwnerInvoice(
        owner_id=owner_id,
        month=month,
        invoice_id=_stable_invoice_id(owner_id, month),
    )

    for prop_id in property_ids:
        prop = PROPERTIES[prop_id]
        revenue = MONTHLY_REVENUE.get(prop_id, 0)
        mgmt_pct = prop["management_contract_pct"]
        mgmt_fee = int(revenue * mgmt_pct)
        platform_fee = int(revenue * _PLATFORM_FEE_PCT)
        total_fee = mgmt_fee + platform_fee

        line = InvoiceLine(
            property_id=prop_id,
            property_name=prop["name"],
            revenue_cents=revenue,
            fee_pct=mgmt_pct + _PLATFORM_FEE_PCT,
            fee_cents=total_fee,
            description=(
                f"{int(mgmt_pct * 100)}% mgmt + 0.5% platform on "
                f"${revenue / 100:.2f} revenue"
            ),
        )
        invoice.line_items.append(line)
        invoice.total_revenue_cents += revenue
        invoice.total_fee_cents += total_fee

    _logger.info(
        "ubp: owner=%s month=%s invoice=%s total_fee=%d",
        owner_id, month, invoice.invoice_id, invoice.total_fee_cents,
    )
    return invoice
