"""
invoice_ingest_skill.py — Parse invoices, detect recurring subscriptions, produce graph records.

Exports: skill (registered on import)
"""

from __future__ import annotations

from gbrain.invoice_ingestion import detect_recurring, ingest_to_graph_records

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "invoices": {
            "type": "array",
            "description": "List of raw invoice dicts (vendor, amount, date).",
        },
    },
    "required": ["invoices"],
}


def _run(args: dict) -> dict:
    """Detect recurring vendors and produce GBrain graph records."""
    invoices: list[dict] = args["invoices"]
    recurring = detect_recurring(invoices)
    records = ingest_to_graph_records(invoices)
    node_records = [r for r in records if r.get("record_type") == "node"]
    edge_records = [r for r in records if r.get("record_type") == "edge"]
    return {
        "recurring": recurring,
        "graph_node_count": len(node_records),
        "graph_edge_count": len(edge_records),
        "graph_records": records,
    }


skill = register(Skill(
    name="invoice_ingest_skill",
    description="Parse invoices, detect recurring subscriptions, and produce GBrain graph records.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
