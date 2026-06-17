"""Knowledge graph read routes for nemoclaw-smb.

Exports (via router):
    GET /graph          — full {nodes, edges} payload for force-graph UI
    GET /graph/vendors  — summarized vendor list with category and payment count
"""

from fastapi import APIRouter

from api.state import graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def get_graph() -> dict:
    """Return all nodes and edges from the singleton knowledge graph."""
    return {"nodes": graph.nodes(), "edges": graph.edges()}


@router.get("/vendors")
def get_vendors() -> list[dict]:
    """Return a summary list of vendors: id, label, category, payment_count."""
    nodes = [n for n in graph.nodes() if n.get("type") == "vendor"]
    edges = graph.edges()
    payment_counts: dict[str, int] = {}
    for edge in edges:
        target = edge.get("target", "")
        payment_counts[target] = payment_counts.get(target, 0) + 1

    return [
        {
            "id": n["id"],
            "label": n["label"],
            "category": n.get("category"),
            "payment_count": payment_counts.get(n["id"], 0),
        }
        for n in nodes
    ]
