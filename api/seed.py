"""Idempotent demo seeding for the nemoclaw-smb FastAPI app.

Exports:
    DEMO_AUDIT_PATH  - path used by all seeded audit writes
    seed_demo()      - load invoices into graph + run Adobe 402 once; no-op on repeat
    reset_demo()     - clear seed flag so seed_demo() will run again (for tests)
"""

from __future__ import annotations

from pathlib import Path

from api.state import graph
from fixtures.seed_data import adobe_anomaly_402
from payments.payment_402_handler import handle_402

DEMO_AUDIT_PATH: Path = Path("audit/demo_audit.jsonl")
DEMO_INTERACTIONS_PATH: Path = Path("audit/demo_interactions.jsonl")

# Module-level guard: True after first successful seed run.
#GLOBAL-STATE: prevents double-seeding across multiple startup calls in the same process
_seeded: bool = False


def seed_demo() -> None:
    """Seed graph with invoice history and run Adobe escalation once.

    Idempotent: the module flag `_seeded` prevents a second run.
    The audit file path is `audit/demo_audit.jsonl` (gitignored via audit/*.jsonl).
    """
    global _seeded
    if _seeded:
        return

    DEMO_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Graph is already pre-loaded by api/state.py (seed_invoices via build_graph_from_invoices).
    # Run handle_402 on the June Adobe anomaly so /approvals/pending and the audit chain
    # have at least one entry.  The anomaly spikes above the $500 default threshold
    # and is flagged, so outcome will be 'escalated'.
    event = adobe_anomaly_402()
    handle_402(event, graph, audit_path=str(DEMO_AUDIT_PATH))

    # Sponsor interactions are no longer seeded with canned data. The live + historical
    # feed fills from real Hermes / Nemotron / Stripe / C1 calls as the acts run.
    _seeded = True


def reset_demo() -> None:
    """Clear the seed flag and remove the demo audit file.

    Called by tests to restore a clean state between runs.
    """
    global _seeded
    _seeded = False
    if DEMO_AUDIT_PATH.exists():
        DEMO_AUDIT_PATH.unlink()
    if DEMO_INTERACTIONS_PATH.exists():
        DEMO_INTERACTIONS_PATH.unlink()
