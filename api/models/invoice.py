"""Pydantic v2 request/response models for invoice and approval endpoints.

Exports:
    Invoice402Event   — body model for POST /webhooks/402
    ApprovalDecision  — body model for POST /approvals/{request_id}/decide
"""

from pydantic import BaseModel, Field


class Invoice402Event(BaseModel):
    """Inbound HTTP-402 vendor invoice trigger event."""

    vendor: str = Field(..., description="Vendor display name (e.g. 'AWS')")
    amount: float = Field(..., gt=0, description="Invoice amount in USD")
    date: str = Field(..., description="Invoice date as ISO-8601 string (YYYY-MM-DD)")
    invoice_id: str = Field(..., description="Unique invoice identifier")
    trigger: str = Field(default="http_402", description="Event source (e.g. 'http_402')")


class ApprovalDecision(BaseModel):
    """Human decision payload for a pending spend-approval request."""

    approved: bool = Field(..., description="True to approve, False to deny")
    decided_by: str = Field(..., description="Identity of the human approver")
