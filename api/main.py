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

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import approvals, audit, graph, integrations, invoices, savings, str_acts, webhooks
from api.routes import tenant as tenant_routes
from api.seed import seed_demo
from payments.mpp_server import app as mpp_app

# Only the reasoning keys the LIVE toggle needs are loaded at startup. Operational
# config (spend threshold, C1 / Stripe / Intuit creds, sandbox) is deliberately NOT
# pulled in so a running server matches test behavior and nothing finance-adjacent or
# external changes by side effect.
_LIVE_ENV_KEYS = (
    "NOUS_PORTAL_API_KEY",
    "NOUS_PORTAL_BASE_URL",
    "NVIDIA_NIM_API_KEY",
    "NVIDIA_NIM_BASE_URL",
    "HERMES_MODEL",
    "NEMOTRON_MODEL",
)


def _load_dotenv() -> None:
    """Load only the LIVE-toggle reasoning keys from .env into os.environ.

    setdefault, never overwrite a real env var. Mirrors the plain parser in
    verification/reality_report.py. Scoped to _LIVE_ENV_KEYS so a plain `make dev`
    enables the Nous / NVIDIA LIVE path without injecting finance / policy / Stripe
    config that would change unrelated subsystems. No-op when .env is absent.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key in _LIVE_ENV_KEYS:
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


_load_dotenv()


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
app.include_router(integrations.router)

# Fold the standalone MPP HTTP-402 earn server into the main API under /mpp.
app.mount("/mpp", mpp_app)


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "nemoclaw-smb"}
