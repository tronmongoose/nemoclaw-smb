"""
access_governance_skill.py — ConductorOne/Baton access-governance skill for NemoClaw SMB.

Exports: skill (registered on import)
"""

from __future__ import annotations

from control_plane.baton_client import fetch_access, summarize_seats, unused_seats
from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "connector": {
            "type": "string",
            "description": "Baton connector name (e.g. baton-okta). Optional.",
        },
        "c1z_path": {
            "type": "string",
            "description": "Path to a .c1z snapshot file. Optional.",
        },
        "reference_date": {
            "type": "string",
            "description": "ISO date string for unused-seat cutoff. Defaults to today.",
        },
        "days": {
            "type": "integer",
            "description": "Inactivity threshold in days (default 60).",
            "default": 60,
        },
        "graph": {
            "type": "object",
            "description": "KnowledgeGraph instance to annotate with access edges. Optional.",
        },
    },
}


def _run(args: dict) -> dict:
    """Fetch access grants, summarize seats, flag unused, optionally annotate graph."""
    connector = args.get("connector")
    c1z_path = args.get("c1z_path")
    reference_date: str | None = args.get("reference_date")
    days: int = int(args.get("days", 60))
    graph = args.get("graph")

    grants, source = fetch_access(connector=connector, c1z_path=c1z_path)
    seat_summary = summarize_seats(grants)
    idle = unused_seats(grants, days=days, reference_date=reference_date)

    if graph is not None:
        _annotate_graph(graph, grants)

    recommendations = [
        f"deprovision {g.principal} from {g.resource} (unused {days}d)"
        for g in idle
    ]

    return {
        "grants_count": len(grants),
        "seat_summary": seat_summary,
        "unused_seats": [
            {"principal": g.principal, "resource": g.resource, "last_used": g.last_used}
            for g in idle
        ],
        "recommendations": recommendations,
        "source": source,
    }


def _annotate_graph(graph, grants: list) -> None:
    """Add user->app access edges to a KnowledgeGraph without breaking existing shape."""
    seen_resources: set[str] = set()
    for g in grants:
        if g.resource not in seen_resources:
            if not graph.is_known_vendor(g.resource):
                graph.add_vendor(g.resource, category="SaaS/Access")
            seen_resources.add(g.resource)


skill = register(Skill(
    name="access_governance_skill",
    description=(
        "ConductorOne/Baton access-governance: fetch grants, summarize seats, "
        "flag unused seats, and recommend deprovisioning candidates."
    ),
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
