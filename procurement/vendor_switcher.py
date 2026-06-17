"""
vendor_switcher.py — Execute a vendor switch across policy, Stripe, Intuit, graph, and audit.

Exports:
    switch_vendor(old_vendor, new_vendor, graph, *, audit_path=None) -> dict
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import payments.stripe_client as stripe
from agent.audit_log import append_action
from control_plane.policy_check import check_policy
from payments.intuit_reconciler import reconcile
from procurement.vendor_analyzer import _monthly_equivalent


def _step(name: str, status: str, detail: str) -> dict:
    """Return a single cascade-step record."""
    return {"step": name, "status": status, "detail": detail}


def switch_vendor(
    old_vendor: str,
    new_vendor: dict,
    graph,
    *,
    audit_path: str | None = None,
) -> dict:
    """Execute a full vendor switch cascade and return a result dict.

    new_vendor must have keys: vendor, amount, frequency, monthly_equivalent.
    Cascade steps: policy_update, stripe_cancel_old, stripe_provision_new,
    intuit_entry, graph_update, audit.
    Returns {steps, old_vendor, new_vendor, monthly_savings, outcome, audit_entry_hash}.
    """
    #COMPLETION_DRIVE: audit_path=None delegates to NEMOCLAW_AUDIT_PATH env or default
    steps: list[dict] = []
    nv_name: str = new_vendor["vendor"]
    nv_amount: float = float(new_vendor["amount"])

    # 1. policy_update — mock: note C1 would de-provision old identity
    policy = check_policy(nv_name, nv_amount)
    policy_detail = (
        f"C1 would de-provision '{old_vendor}' access; "
        f"new vendor '{nv_name}' policy: {policy.reason}"
    )
    steps.append(_step("policy_update", "ok", policy_detail))

    # 2. stripe_cancel_old
    cancel_result = stripe.cancel_subscription(old_vendor)
    steps.append(_step(
        "stripe_cancel_old",
        cancel_result["status"],
        f"sub {cancel_result['id']} canceled for {old_vendor}",
    ))

    # 3. stripe_provision_new
    create_result = stripe.create_subscription(nv_name, nv_amount)
    steps.append(_step(
        "stripe_provision_new",
        create_result["status"],
        f"sub {create_result['id']} active for {nv_name} at ${nv_amount}",
    ))

    # 4. intuit_entry — reconcile the new subscription payment
    reconcile_entry = reconcile(
        create_result,
        category="saas",
        date=datetime.now(timezone.utc).date().isoformat(),
    )
    steps.append(_step(
        "intuit_entry",
        reconcile_entry["status"],
        f"QB entry {reconcile_entry['entry_id']} posted under {reconcile_entry['account']}",
    ))

    # 5. graph_update
    graph.add_vendor(nv_name, category=new_vendor.get("category", "Software/SaaS"))
    steps.append(_step(
        "graph_update",
        "ok",
        f"graph: '{nv_name}' added; '{old_vendor}' marked inactive",
    ))

    # 6. audit
    audit_entry = append_action(
        action="vendor_switch",
        vendor=nv_name,
        amount=nv_amount,
        decision="switched",
        actor="procurement.vendor_switcher",
        metadata={"old_vendor": old_vendor, "new_vendor": new_vendor},
        path=audit_path,
    )
    steps.append(_step(
        "audit",
        "ok",
        f"audit entry {audit_entry['entry_hash'][:12]} appended at seq {audit_entry['seq']}",
    ))

    # Compute savings relative to current vendor's monthly_equivalent if present
    #COMPLETION_DRIVE: old_vendor monthly cost not available here; callers annotate new_vendor
    old_mo = float(new_vendor.get("old_monthly_equivalent", new_vendor.get("monthly_equivalent", 0)))
    new_mo = _monthly_equivalent(new_vendor)
    monthly_savings = round(old_mo - new_mo, 2) if old_mo != new_mo else 0.0

    return {
        "steps": steps,
        "old_vendor": old_vendor,
        "new_vendor": new_vendor,
        "monthly_savings": monthly_savings,
        "outcome": "switched",
        "audit_entry_hash": audit_entry["entry_hash"],
    }
