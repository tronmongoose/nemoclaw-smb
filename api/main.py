"""FastAPI entry point for the NemoClaw SMB Ops Agent.

Mounts three route groups:
    /webhooks   — 402 invoice pipeline + Stripe callback (api/routes/webhooks.py)
    /graph      — knowledge graph read endpoints (api/routes/graph.py)
    /approvals  — spend-approval list + decide (api/routes/approvals.py)
"""

from fastapi import FastAPI

from api.routes import approvals, graph, webhooks

app = FastAPI(title="NemoClaw SMB Ops Agent", version="0.1.0")

app.include_router(webhooks.router)
app.include_router(graph.router)
app.include_router(approvals.router)


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "nemoclaw-smb"}
