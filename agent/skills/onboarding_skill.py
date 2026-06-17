"""
onboarding_skill.py — Build a vendor knowledge graph from a studio profile + invoices.

Exports: skill (registered on import)
"""

from __future__ import annotations

from fixtures.seed_data import seed_invoices, studio_profile
from gbrain.knowledge_graph import build_graph_from_invoices

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "invoices": {
            "type": "array",
            "description": "Raw invoice dicts; omit to use demo seed data.",
        },
    },
    "required": [],
}


def _run(args: dict) -> dict:
    """Build a knowledge graph and return node/edge counts + vendor list."""
    invoices = args.get("invoices") or seed_invoices()
    profile = studio_profile()
    graph = build_graph_from_invoices(invoices)
    nodes = graph.nodes()
    edges = graph.edges()
    vendors = [n["label"] for n in nodes if n.get("type") == "vendor"]
    return {
        "studio": profile["name"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "vendor_count": len(vendors),
        "vendors": vendors,
    }


skill = register(Skill(
    name="onboarding_skill",
    description="Ingest a studio profile and invoice history into a vendor knowledge graph.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
