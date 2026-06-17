"""
handle_402_skill.py — Full NemoClaw HTTP-402 pipeline for a single vendor invoice event.

Exports: skill (registered on import)
"""

from __future__ import annotations

from gbrain.knowledge_graph import build_graph_from_invoices
from payments.payment_402_handler import handle_402

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "event": {
            "type": "object",
            "description": "Invoice event dict: vendor, amount, date, invoice_id, trigger.",
        },
        "invoices": {
            "type": "array",
            "description": "Prior invoice history to build the knowledge graph from.",
        },
        "threshold": {
            "type": "number",
            "description": "Spend approval threshold in USD (default 500).",
            "default": 500.0,
        },
    },
    "required": ["event", "invoices"],
}


def _run(args: dict) -> dict:
    """Build graph from history, run the 402 pipeline, return structured outcome."""
    event: dict = args["event"]
    invoices: list[dict] = args["invoices"]
    threshold: float | None = args.get("threshold")

    graph = build_graph_from_invoices(invoices)
    outcome = handle_402(event, graph, threshold=threshold)
    return outcome


skill = register(Skill(
    name="handle_402_skill",
    description="Run the full NemoClaw HTTP-402 pipeline: gbrain lookup, policy, anomaly, pay or escalate.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
