"""Idempotent demo seeding for the nemoclaw-smb FastAPI app.

Exports:
    DEMO_AUDIT_PATH  — path used by all seeded audit writes
    seed_demo()      — load invoices into graph + run Adobe 402 once; no-op on repeat
    reset_demo()     — clear seed flag so seed_demo() will run again (for tests)
"""

from __future__ import annotations

from pathlib import Path

from agent.interactions_log import append_interaction, read_interactions
from api.state import graph
from fixtures.seed_data import adobe_anomaly_402
from payments.payment_402_handler import handle_402

DEMO_AUDIT_PATH: Path = Path("audit/demo_audit.jsonl")
DEMO_INTERACTIONS_PATH: Path = Path("audit/demo_interactions.jsonl")

# (sponsor, op, segment, status, model, latency_ms, mode, metadata)
_DEMO_INTERACTIONS = [
    ("NVIDIA", "anomaly reasoning", "owner", "ok", "nvidia/nemotron-3-ultra-550b-a55b", 20040.0, "live", {}),
    ("ConductorOne", "authorize NHI", "owner", "ok", None, 2.6, None, {"source": "baton-carryall"}),
    ("Stripe", "reconciliation payout", "owner", "ok", None, None, None, {"amount_cents": 8400}),
    ("Stripe", "card issue (Issuing for Agents)", "firm", "ok", None, None, None, {"amount_cents": 7500}),
    ("Stripe", "crew payout (Connect + Global Payouts)", "firm", "ok", None, None, None, {"amount_cents": 42000}),
    ("Stripe", "owner account (Connect)", "firm", "ok", None, None, None, {}),
    ("Stripe", "UBP invoice (Metronome)", "firm", "ok", None, None, None, {"amount_cents": 29200}),
    ("Nous Research", "intent orchestration", "agent", "ok", "nvidia/nemotron-3-super-120b-a12b", 1840.0, "live", {}),
    ("NVIDIA", "AEO scoring", "agent", "cached", "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]", 0.0, "demo", {}),
    ("NVIDIA", "dynamic pricing", "agent", "cached", "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]", 0.0, "demo", {}),
    ("Stripe", "MPP earn: aeo-audit", "agent", "ok", None, None, None, {"amount_cents": 100}),
    ("Stripe", "MPP earn: price", "agent", "ok", None, None, None, {"amount_cents": 25}),
]

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

    # Seed historical sponsor interactions once (restart-idempotent: only when empty),
    # so the live + historical feed has content before any act runs. Live interactions
    # append to the same chain as acts execute.
    if not read_interactions(limit=1, path=DEMO_INTERACTIONS_PATH):
        for sponsor, op, segment, status, model, latency, mode, meta in _DEMO_INTERACTIONS:
            append_interaction(
                sponsor=sponsor, op=op, segment=segment, status=status,
                model=model, latency_ms=latency, mode=mode, metadata=meta,
                path=DEMO_INTERACTIONS_PATH,
            )

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
