"""
pay_invoice_skill.py — Atomic Stripe payment step for a single vendor invoice.

Called exclusively through nemoclaw_harness.execute() so that the spend gate,
guardrail, and audit chain are owned by the harness, not the caller.

Exports: skill (registered on import)
"""

from __future__ import annotations

from payments import stripe_client

from agent.skills.base import Skill, register

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string", "description": "Vendor name for the payment."},
        "amount": {"type": "number", "description": "Invoice amount in USD."},
        "invoice_id": {"type": "string", "description": "Idempotency key / invoice identifier."},
    },
    "required": ["vendor", "amount", "invoice_id"],
}


def _run(args: dict) -> dict:
    """Execute the Stripe payment and return the payment result dict."""
    vendor: str = args["vendor"]
    amount: float = float(args["amount"])
    invoice_id: str = args["invoice_id"]
    return stripe_client.pay(vendor, amount, idempotency_key=invoice_id)


skill = register(Skill(
    name="pay_invoice_skill",
    description="Charge a vendor invoice via Stripe (MCP -> SDK -> mock). Called through nemoclaw_harness only.",
    input_schema=_INPUT_SCHEMA,
    run=_run,
))
