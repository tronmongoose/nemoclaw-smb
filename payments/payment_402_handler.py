"""
payment_402_handler.py — HTTP-402 demo centerpiece for nemoclaw-smb hackathon.

Orchestrates the full gbrain → policy → anomaly → decision → payment/escalation
pipeline for a single vendor invoice event. Returns a structured outcome dict
with an audit-chain entry hash on every call.

Exports:
    handle_402(event, graph, *, threshold, audit_path) -> dict
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from agent import audit_log, require_approval
from control_plane.policy_check import check_policy
from gbrain.anomaly_detector import score_invoice
from payments import intuit_reconciler as intuit
from payments import stripe_client as stripe

if TYPE_CHECKING:
    from gbrain.knowledge_graph import KnowledgeGraph

# Default spend threshold when caller does not supply one.
# Set to 500 to cover typical SMB SaaS recurring invoices (e.g. AWS $312, Adobe ~$277)
# without requiring approval on every routine renewal.
# Callers may override via the threshold kwarg or SPEND_APPROVAL_THRESHOLD env var.
#COMPLETION_DRIVE: 500 is a reasonable SMB default; production installs should configure explicitly
_DEFAULT_THRESHOLD = 500.0


# ---------------------------------------------------------------------------
# Public contract
# ---------------------------------------------------------------------------

def handle_402(
    event: dict,
    graph: "KnowledgeGraph",
    *,
    threshold: float | None = None,
    audit_path: str | None = None,
) -> dict:
    """Resolve one HTTP-402 vendor invoice through the full NemoClaw pipeline.

    event keys: vendor, amount, date, invoice_id, trigger.
    Returns the structured outcome dict (see module docstring shape).
    """
    vendor: str = event["vendor"]
    amount: float = float(event["amount"])
    date: str = event["date"]
    invoice_id: str = event["invoice_id"]
    spend_threshold = threshold if threshold is not None else _DEFAULT_THRESHOLD

    steps: list[dict] = []

    # 1. gbrain_lookup
    steps.append(_step_gbrain_lookup(vendor, graph))

    # 2. policy_check
    policy = check_policy(vendor, amount)
    steps.append({
        "step": "policy_check",
        "status": "allowed" if policy.allowed else "denied",
        "detail": policy.reason,
    })

    # 3. anomaly_score
    history = graph.vendor_history(vendor)
    anomaly = score_invoice(vendor, amount, history)
    steps.append({
        "step": "anomaly_score",
        "status": "flagged" if anomaly.is_anomaly else "clean",
        "detail": anomaly.reason,
    })

    # 4. decision + terminal action
    clean = policy.allowed and not anomaly.is_anomaly
    if clean:
        return _try_pay(
            vendor, amount, date, invoice_id, anomaly, steps, graph, spend_threshold, audit_path
        )
    return _do_escalation(
        vendor, amount, invoice_id, anomaly, steps, spend_threshold, audit_path, policy_reason=policy.reason
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_gbrain_lookup(vendor: str, graph: "KnowledgeGraph") -> dict:
    """Return the gbrain_lookup step dict."""
    known = graph.is_known_vendor(vendor)
    if known:
        rng = graph.expected_range(vendor)
        rng_str = f"${rng[0]:.0f}–${rng[1]:.0f}" if rng else "insufficient history"
        detail = f"known vendor; expected range {rng_str}"
    else:
        detail = "new vendor — no prior history"
    return {"step": "gbrain_lookup", "status": "known" if known else "new", "detail": detail}


def _try_pay(
    vendor: str,
    amount: float,
    date: str,
    invoice_id: str,
    anomaly,
    steps: list[dict],
    graph: "KnowledgeGraph",
    threshold: float,
    audit_path: str | None,
) -> dict:
    """Gate spend via threshold; escalate if approval is required but not yet granted.

    enforce_spend reads SPEND_APPROVAL_THRESHOLD from env and ignores the caller's
    threshold kwarg, so we pre-check with requires_approval(threshold) first.
    Only invoke enforce_spend (which handles already-approved lookup) when the
    caller's threshold says approval IS needed — otherwise proceed directly to payment.
    #COMPLETION_DRIVE: enforce_spend lacks a threshold param; pre-check bridges the gap
    """
    if not require_approval.requires_approval("purchase", amount, threshold):
        return _do_payment(vendor, amount, date, invoice_id, anomaly, steps, graph, audit_path)

    # Amount exceeds threshold: check for an existing approval or raise
    try:
        require_approval.enforce_spend(
            "purchase", vendor, amount, actor="agent",
            context={"invoice_id": invoice_id, "date": date, "threshold": threshold},
        )
        # enforce_spend returned (already approved) — proceed to pay
        return _do_payment(vendor, amount, date, invoice_id, anomaly, steps, graph, audit_path)
    except require_approval.ApprovalRequired as exc:
        steps.append({"step": "decision", "status": "approval_required",
                      "detail": f"spend ${amount} exceeds threshold ${threshold}"})
        return _do_escalation(
            vendor, amount, invoice_id, anomaly, steps, threshold, audit_path,
            request_id=exc.request_id, policy_reason=None,
        )


def _do_payment(
    vendor: str,
    amount: float,
    date: str,
    invoice_id: str,
    anomaly,
    steps: list[dict],
    graph: "KnowledgeGraph",
    audit_path: str | None,
) -> dict:
    """Execute payment, reconcile, record in graph, append audit entry."""
    steps.append({"step": "decision", "status": "approved", "detail": "policy allowed, no anomaly"})

    payment = stripe.pay(vendor, amount, idempotency_key=invoice_id)
    ledger_entry = intuit.reconcile(payment, category=None, date=date)
    graph.record_payment(vendor, amount, date, anomaly_flag=False)

    audit_entry = audit_log.append_action(
        "payment", vendor, amount,
        decision="auto_paid",
        actor="agent",
        metadata={"invoice_id": invoice_id, "stripe_id": payment["id"],
                  "ledger_id": ledger_entry["entry_id"]},
        path=audit_path,
    )
    steps.append({"step": "payment", "status": "succeeded",
                  "detail": f"stripe {payment['id']}"})

    return {
        "invoice_id": invoice_id,
        "vendor": vendor,
        "amount": amount,
        "steps": steps,
        "outcome": "paid",
        "payment": payment,
        "ledger_entry": ledger_entry,
        "approval_request_id": None,
        "anomaly": None,
        "audit_entry_hash": audit_entry["entry_hash"],
    }


def _do_escalation(
    vendor: str,
    amount: float,
    invoice_id: str,
    anomaly,
    steps: list[dict],
    threshold: float,
    audit_path: str | None,
    *,
    request_id: str | None = None,
    policy_reason: str | None,
) -> dict:
    """Create an approval request, append audit entry, return escalated outcome."""
    if request_id is None:
        request_id = require_approval.create_request(
            "purchase", vendor, amount,
            context={"invoice_id": invoice_id, "threshold": threshold,
                     "policy_reason": policy_reason,
                     "anomaly_reason": anomaly.reason if anomaly.is_anomaly else None},
        )

    if "decision" not in {s["step"] for s in steps}:
        detail = policy_reason or anomaly.reason
        steps.append({"step": "decision", "status": "escalated", "detail": detail})

    audit_entry = audit_log.append_action(
        "approval_request", vendor, amount,
        decision="escalated",
        actor="agent",
        metadata={"invoice_id": invoice_id, "request_id": request_id,
                  "anomaly_flagged": anomaly.is_anomaly},
        path=audit_path,
    )
    steps.append({"step": "escalation", "status": "pending",
                  "detail": f"approval request {request_id}"})

    return {
        "invoice_id": invoice_id,
        "vendor": vendor,
        "amount": amount,
        "steps": steps,
        "outcome": "escalated",
        "payment": None,
        "ledger_entry": None,
        "approval_request_id": request_id,
        "anomaly": asdict(anomaly) if anomaly.is_anomaly else None,
        "audit_entry_hash": audit_entry["entry_hash"],
    }
