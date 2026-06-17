"""FastAPI entry point for the NemoClaw SMB Ops Agent.

Routes are mounted from api/routes as the build progresses (onboarding, invoices,
approvals, webhooks). This module currently exposes a health check so the stack boots.
"""

from fastapi import FastAPI

app = FastAPI(title="NemoClaw SMB Ops Agent", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "nemoclaw-smb"}
