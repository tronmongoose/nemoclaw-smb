"""FastAPI entry point for the NemoClaw SMB Ops Agent.

Mounts route groups:
    /webhooks   - 402 invoice pipeline + Stripe callback (api/routes/webhooks.py)
    /graph      - knowledge graph read endpoints (api/routes/graph.py)
    /approvals  - spend-approval list + decide (api/routes/approvals.py)
    /invoices   - invoice list + anomaly scan (api/routes/invoices.py)
    /savings    - vendor alternatives + savings summary (api/routes/savings.py)
    /audit      - demo audit chain read + verify (api/routes/audit.py)
    /str        - the three STR acts over HTTP (api/routes/str_acts.py)
    /mpp        - MPP HTTP-402 earn server folded in (payments/mpp_server.app)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import approvals, audit, graph, invoices, savings, str_acts, webhooks
from api.routes import tenant as tenant_routes
from api.seed import seed_demo
from payments.mpp_server import app as mpp_app


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
app.include_router(str_acts.router)
app.include_router(tenant_routes.router)

# Fold the standalone MPP HTTP-402 earn server into the main API under /mpp.
app.mount("/mpp", mpp_app)


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "nemoclaw-smb"}
