"""Approval management routes for nemoclaw-smb spend-gate decisions.

Exports (via router):
    GET  /approvals/pending              — list all pending approval requests
    POST /approvals/{request_id}/decide  — record a human approval or denial
"""

from fastapi import APIRouter, HTTPException

from agent import require_approval
from api.models.invoice import ApprovalDecision

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/pending")
def list_pending() -> list[dict]:
    """Return all pending (non-expired) spend-approval requests."""
    return require_approval.list_pending()


@router.post("/{request_id}/decide")
def decide(request_id: str, body: ApprovalDecision) -> dict:
    """Record a human decision on a pending approval request."""
    try:
        return require_approval.decide(request_id, body.approved, body.decided_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
