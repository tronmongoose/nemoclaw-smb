"""FastAPI entry point for the NemoClaw SMB Ops Agent.

Mounts route groups:
    /webhooks   — 402 invoice pipeline + Stripe callback (api/routes/webhooks.py)
    /graph      — knowledge graph read endpoints (api/routes/graph.py)
    /approvals  — spend-approval list + decide (api/routes/approvals.py)
    /invoices   — invoice list + anomaly scan (api/routes/invoices.py)
    /savings    — vendor alternatives + savings summary (api/routes/savings.py)
    /audit      — demo audit chain read + verify (api/routes/audit.py)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import approvals, graph, webhooks
from api.routes import audit, invoices, savings, tenant as tenant_routes
from api.seed import seed_demo


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Run idempotent demo seeding once before serving requests."""
    seed_demo()
    yield


app = FastAPI(title="NemoClaw SMB Ops Agent", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(graph.router)
app.include_router(approvals.router)
app.include_router(invoices.router)
app.include_router(savings.router)
app.include_router(audit.router)
app.include_router(tenant_routes.router)


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "nemoclaw-smb"}
