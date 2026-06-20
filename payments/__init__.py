"""payments -- Stripe payment primitives for NemoClaw SMB agent.

Exports:
    envelopes    -- Ed25519 signed envelopes for Stripe writes
    issuing      -- Stripe Issuing single-use cleaner cards
    payouts      -- Global Payouts for crew
    connect      -- Stripe Connect multi-owner accounts
    metronome    -- Usage-based billing invoices
"""
from payments.connect import ConnectedAccount, ensure_owner_accounts, get_connected_account
from payments.issuing import CleanerCardResult, RevokeResult, issue_cleaner_card, revoke_card
from payments.metronome import OwnerInvoice, calculate_ubp
from payments.payouts import PayoutBatch, PayoutRecord, run_payouts

# mpp_server pulls in FastAPI; import it directly as payments.mpp_server where the
# MPP earn server runs. Keeping it out of the package import avoids dragging
# FastAPI into every consumer of payments and keeps the 3.9 test collection clean.

__all__ = [
    "CleanerCardResult",
    "RevokeResult",
    "issue_cleaner_card",
    "revoke_card",
    "PayoutBatch",
    "PayoutRecord",
    "run_payouts",
    "ConnectedAccount",
    "ensure_owner_accounts",
    "get_connected_account",
    "OwnerInvoice",
    "calculate_ubp",
]
