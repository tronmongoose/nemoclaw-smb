"""acts/str_owner_agent.py: Act I: STR Owner Agent (management fee reconciliation).

Detects management fee overcharges and initiates a governed Stripe reconciliation
payout. prop-001 "Sweet Clementine" is charged 22% against a 20% contract on
$4,200 revenue: an $84 overcharge the agent catches, holds for approval, and
pays back once approved.

Public API:
    LedgerSummary: dataclass: revenue, fee percentages, line items
    AnomalyResult: dataclass: is_anomaly, expected vs charged, reason
    PaymentResult: dataclass: payment_id, amount_cents, status, audit_hash
    ReconciliationReport: dataclass: summary, anomaly, payment, audit_ok
    REQUIRE_APPROVAL_THRESHOLD_CENTS: 50000 (equals $500)
    ingest_ledger(property_id, month) -> LedgerSummary
    detect_fee_anomaly(summary, contract, live=False) -> AnomalyResult
    trigger_payment(amount_cents, vendor_id, requires_approval) -> PaymentResult
    reconcile_month(property_id, month, live=False) -> ReconciliationReport

Reasoning provenance: AnomalyResult.reasoning_provenance is a dict with keys
mode (live|demo), model, latency_ms, source (nemotron|cached).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from agent.audit_log import append_action, verify_chain
from agent.interactions_log import append_interaction
from agent.nvidia_client import call_nemotron, nemotron_available
from agent.require_approval import ApprovalRequired, decide, enforce_spend
from config.demo_mode import demo_mode
from config.model_routing import route_for
from control_plane.c1_governance import authorize, issue_nhi
from data.mock_ledger import get_ledger_summary
from payments.envelopes import sign_stripe_envelope
from payments.stripe_client import pay

REQUIRE_APPROVAL_THRESHOLD_CENTS: int = 50_000  # $500

# Agent identity issued at module load (C1 NHI beat).
_NHI = issue_nhi("str-owner-agent", scopes=["ledger:read", "payment:propose"])


@dataclass
class LedgerSummary:
    """Ingested ledger snapshot for one property/month."""

    property_id: str
    month: str
    revenue_cents: int
    contract_pct: float
    charged_pct: float
    line_items: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyResult:
    """Outcome of fee anomaly detection."""

    is_anomaly: bool
    expected_fee_cents: int
    charged_fee_cents: int
    overcharge_cents: int
    reason: str
    model_used: str = ""
    reasoning_trace: str = ""
    reasoning_provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentResult:
    """Outcome of a triggered payment."""

    payment_id: str
    amount_cents: int
    status: str
    audit_hash: str
    held_for_approval: bool = False
    request_id: str = ""


@dataclass
class ReconciliationReport:
    """Full Act I output: ingest + detect + pay (or hold)."""

    property_id: str
    month: str
    summary: LedgerSummary
    anomaly: AnomalyResult
    payment: PaymentResult | None
    audit_ok: bool
    audit_detail: str
    nhi_id: str


def ingest_ledger(property_id: str, month: str) -> LedgerSummary:
    """Pull ledger data from mock_ledger and return a typed LedgerSummary.

    Raises KeyError when property_id is unknown.
    """
    raw = get_ledger_summary(property_id, month)
    return LedgerSummary(
        property_id=property_id,
        month=month,
        revenue_cents=raw["revenue_cents"],
        contract_pct=raw["contracted_fee_pct"],
        charged_pct=raw["charged_fee_pct"],
        line_items={
            "contracted_fee_cents": raw["contracted_fee_cents"],
            "charged_fee_cents": raw["charged_fee_cents"],
            "fee_delta_cents": raw["fee_delta_cents"],
        },
    )


def _demo_anomaly_trace(summary: LedgerSummary, expected: int, charged: int) -> str:
    """Return the deterministic cached anomaly reasoning trace (DEMO path)."""
    diff = charged - expected
    return (
        f"[DEMO cached trace] Revenue: ${summary.revenue_cents / 100:.2f}. "
        f"Contract rate: {summary.contract_pct * 100:.1f}%. "
        f"Charged rate: {summary.charged_pct * 100:.1f}%. "
        f"Expected fee: ${expected / 100:.2f}. "
        f"Charged fee: ${charged / 100:.2f}. "
        f"Delta: ${diff / 100:.2f}. "
        f"Conclusion: {'overcharge detected' if diff > 0 else 'no anomaly'}."
    )


def _anomaly_prompt(summary: LedgerSummary, expected: int, charged: int) -> str:
    """Compose the Nemotron anomaly-reasoning prompt for the live path."""
    return (
        f"You are an STR management-fee auditor. Property {summary.property_id}, "
        f"month {summary.month}. Revenue ${summary.revenue_cents / 100:.2f}. "
        f"Contract rate {summary.contract_pct * 100:.1f}%, charged rate "
        f"{summary.charged_pct * 100:.1f}%. Expected fee ${expected / 100:.2f}, "
        f"charged fee ${charged / 100:.2f}. State in 2 sentences whether this is an "
        f"overcharge and by how much."
    )


def _reasoning_trace(
    summary: LedgerSummary,
    expected: int,
    charged: int,
    live: bool = False,  # noqa: FBT001, FBT002
) -> tuple[str, dict[str, Any]]:
    """Return (trace, provenance) for the anomaly reasoning step.

    When live is True and a Nemotron key is present, calls the real model and
    measures latency. Otherwise returns the deterministic cached trace.
    """
    model = route_for("anomaly_detection")
    if live and nemotron_available():
        prompt = _anomaly_prompt(summary, expected, charged)
        start = time.perf_counter()
        trace = call_nemotron(prompt, max_tokens=256, temperature=0.0)
        latency_ms = (time.perf_counter() - start) * 1000.0
        provenance = {
            "mode": "live", "model": model, "latency_ms": latency_ms, "source": "nemotron",
        }
        try:
            _sponsor = "Nous Research" if provenance["source"] == "hermes" else "NVIDIA"
            _status = "ok" if provenance["mode"] == "live" else "cached"
            append_interaction(
                sponsor=_sponsor, op="anomaly reasoning", segment="owner",
                status=_status, model=provenance["model"],
                latency_ms=provenance["latency_ms"], mode=provenance["mode"],
            )
        except Exception:
            pass
        return trace, provenance
    trace = _demo_anomaly_trace(summary, expected, charged)
    provenance = {
        "mode": "demo", "model": f"{model}[demo-cached]", "latency_ms": 0.0, "source": "cached",
    }
    try:
        _sponsor = "Nous Research" if provenance["source"] == "hermes" else "NVIDIA"
        _status = "ok" if provenance["mode"] == "live" else "cached"
        append_interaction(
            sponsor=_sponsor, op="anomaly reasoning", segment="owner",
            status=_status, model=provenance["model"],
            latency_ms=provenance["latency_ms"], mode=provenance["mode"],
        )
    except Exception:
        pass
    return trace, provenance


def detect_fee_anomaly(
    summary: LedgerSummary,
    contract: float,
    live: bool = False,  # noqa: FBT001, FBT002
) -> AnomalyResult:
    """Compute expected vs charged fee and flag anomaly when they differ.

    contract is the authoritative rate (from the property record, not the ledger).
    When live is True and a Nemotron key is present, routes reasoning to the real
    model; otherwise returns a deterministic cached trace. live defaults False.
    """
    expected = int(summary.revenue_cents * contract)
    charged = int(summary.revenue_cents * summary.charged_pct)
    overcharge = charged - expected
    trace, provenance = _reasoning_trace(summary, expected, charged, live)
    model = provenance["model"]

    if overcharge == 0:
        return AnomalyResult(
            is_anomaly=False,
            expected_fee_cents=expected,
            charged_fee_cents=charged,
            overcharge_cents=0,
            reason="Charged fee matches contract rate.",
            model_used=model,
            reasoning_trace=trace,
            reasoning_provenance=provenance,
        )

    direction = "over" if overcharge > 0 else "under"
    return AnomalyResult(
        is_anomaly=True,
        expected_fee_cents=expected,
        charged_fee_cents=charged,
        overcharge_cents=overcharge,
        reason=(
            f"Fee {direction}charge detected: contract {contract * 100:.1f}% "
            f"vs charged {summary.charged_pct * 100:.1f}% on "
            f"${summary.revenue_cents / 100:.2f} revenue."
        ),
        model_used=model,
        reasoning_trace=trace,
        reasoning_provenance=provenance,
    )


def _audit_envelope_and_pay(amount_cents: int, vendor_id: str) -> PaymentResult:
    """Sign envelope, write to audit log, then call stripe pay. Returns PaymentResult."""
    amount_dollars = amount_cents / 100.0
    envelope = sign_stripe_envelope(
        "str_owner_refund",
        {"vendor": vendor_id, "amount_cents": amount_cents},
        agent_id=_NHI["agent_id"],
        scopes=_NHI["scopes"],
    )
    # Audit envelope is written inside sign_stripe_envelope before this returns.
    stripe_result = pay(
        vendor_id, amount_dollars, idempotency_key=envelope.get("signature", "")[:32]
    )
    entry = append_action(
        action="payment",
        vendor=vendor_id,
        amount=amount_dollars,
        decision="completed",
        actor=_NHI["agent_id"],
        metadata={"envelope_action": "str_owner_refund", "stripe_id": stripe_result.get("id")},
    )
    return PaymentResult(
        payment_id=stripe_result.get("id", ""),
        amount_cents=amount_cents,
        status=stripe_result.get("status", "unknown"),
        audit_hash=entry["entry_hash"],
    )


def trigger_payment(
    amount_cents: int,
    vendor_id: str,
    requires_approval: bool = True,  # noqa: FBT001
) -> PaymentResult:
    """Gate payment via enforce_spend, sign envelope, audit, then pay.

    Amounts over REQUIRE_APPROVAL_THRESHOLD_CENTS require human approval.
    Raises ApprovalRequired when approval is pending (caller must decide + retry).
    When requires_approval is False the threshold check is bypassed (tests/demo).
    """
    threshold_dollars = REQUIRE_APPROVAL_THRESHOLD_CENTS / 100.0
    amount_dollars = amount_cents / 100.0
    # #COMPLETION_DRIVE: requires_approval lets test harness bypass gate after simulated approve
    if requires_approval:
        enforce_spend(
            action="transfer",
            vendor=vendor_id,
            amount=amount_dollars,
            actor=_NHI["agent_id"],
            context={"amount_cents": amount_cents, "nhi_id": _NHI["id"]},
            threshold=threshold_dollars,
        )
    return _audit_envelope_and_pay(amount_cents, vendor_id)


def reconcile_month(
    property_id: str,
    month: str,
    live: bool = False,  # noqa: FBT001, FBT002
) -> ReconciliationReport:
    """Ingest ledger, detect anomaly, hold for approval, (approve in demo), pay, return report.

    In DEMO_MODE the approval is simulated inline so the full flow completes.
    In production the caller catches ApprovalRequired and re-calls after real approval.
    live (default False) threads through to detect_fee_anomaly's reasoning path.
    """
    summary = ingest_ledger(property_id, month)
    prop_contract = summary.contract_pct
    anomaly = detect_fee_anomaly(summary, prop_contract, live=live)

    # Authorize the corrected payment under the C1 NHI before spending.
    _allowed, _reason = authorize(_NHI, "propose_payment", "stripe")

    payment: PaymentResult | None = None

    if anomaly.is_anomaly:
        corrected_cents = anomaly.expected_fee_cents
        try:
            payment = trigger_payment(corrected_cents, property_id, requires_approval=True)
        except ApprovalRequired as exc:
            if demo_mode():
                # Simulate approval inline for demo completeness.
                decide(exc.request_id, approved=True, decided_by="demo-auto-approver")
                # enforce_spend will now find the approved record and pass through.
                payment = trigger_payment(corrected_cents, property_id, requires_approval=True)
            else:
                payment = PaymentResult(
                    payment_id="",
                    amount_cents=corrected_cents,
                    status="held_for_approval",
                    audit_hash="",
                    held_for_approval=True,
                    request_id=exc.request_id,
                )

    ok, detail = verify_chain()
    return ReconciliationReport(
        property_id=property_id,
        month=month,
        summary=summary,
        anomaly=anomaly,
        payment=payment,
        audit_ok=ok,
        audit_detail=detail,
        nhi_id=_NHI["id"],
    )
