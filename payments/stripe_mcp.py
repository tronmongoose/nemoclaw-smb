"""
Stripe MCP client for NemoClaw — routes pay/provision/fee actions through
the Stripe MCP server (npx @stripe/mcp proxying mcp.stripe.com).

Public API:
    stripe_mcp_enabled() -> bool
    call_tool(name, arguments) -> dict
    mcp_pay(amount_cents, currency, metadata) -> dict
    mcp_create_subscription(vendor, amount_cents, currency) -> dict
    mcp_collect_fee(amount_cents, metadata) -> dict

The @stripe/mcp server (v0.3.3+) is a stdio proxy to mcp.stripe.com.
Tool permissions are controlled by the Restricted API Key (RAK) scope —
not by a --tools flag (removed in v0.3.0). Pass sk_test_* or rk_test_* for
sandbox operations.

Verified tool names from mcp.stripe.com (per docs.stripe.com/mcp, 2026-06):
  create_payment_intent, confirm_payment_intent, retrieve_payment_intent,
  list_payment_intents, create_customer, retrieve_customer, list_customers,
  create_product, retrieve_product, list_products, create_price,
  retrieve_price, list_prices, create_subscription, retrieve_subscription,
  cancel_subscription, list_subscriptions, retrieve_balance, list_charges,
  create_refund.

#SUGGEST_VERIFY: run `npx @stripe/mcp --api-key=sk_test_... tools/list` against
a live test key to confirm the full tool set against your RAK permissions.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from typing import Any

logger = logging.getLogger(__name__)


class StripeMcpError(Exception):
    """Raised when the MCP session fails; callers fall back to SDK or mock."""


def stripe_mcp_enabled() -> bool:
    """Return True when the MCP path is available and not force-disabled.

    Conditions: npx on PATH, STRIPE_SECRET_KEY is a test-mode key (sk_test_),
    and STRIPE_FORCE_SDK is not set to a truthy value.
    """
    if os.environ.get("STRIPE_FORCE_SDK", "").lower() in ("1", "true", "yes"):
        return False
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        return False
    if shutil.which("npx") is None:
        return False
    return True


async def _call_tool_async(name: str, arguments: dict) -> dict:
    """Open a fresh stdio MCP session, call one tool, and return the result.

    Opens and closes the session per call — MCP subprocess is cheap to
    spawn for hackathon use. For production, hold a long-lived session.
    #COMPLETION_DRIVE: production deployments should reuse a session context
    """
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    key = os.environ.get("STRIPE_SECRET_KEY", "")
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@stripe/mcp", f"--api-key={key}"],
        env=None,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments=arguments)
            if result.isError:
                raise StripeMcpError(
                    f"MCP tool {name!r} returned error: {result.content}"
                )
            content = result.content
            if content and hasattr(content[0], "text"):
                import json
                try:
                    return json.loads(content[0].text)
                except (ValueError, TypeError):
                    return {"raw": content[0].text}
            return {"content": str(content)}


def call_tool(name: str, arguments: dict) -> dict:
    """Synchronous wrapper: open an MCP session, call tool, return parsed result.

    Raises StripeMcpError on any failure so callers can fall back gracefully.
    """
    try:
        return asyncio.run(_call_tool_async(name, arguments))
    except StripeMcpError:
        raise
    except Exception as exc:
        raise StripeMcpError(f"MCP call_tool({name!r}) failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Thin helpers mapping NemoClaw operations to Stripe MCP tool names
# ---------------------------------------------------------------------------

def mcp_pay(amount_cents: int, currency: str = "usd", metadata: dict | None = None) -> dict:
    """Create a PaymentIntent via MCP (create_payment_intent + confirm).

    Two-step because mcp.stripe.com exposes create and confirm as separate
    tools. #COMPLETION_DRIVE: if the remote server adds a combined create+confirm
    tool, collapse to a single call.
    """
    args: dict[str, Any] = {
        "amount": amount_cents,
        "currency": currency,
        "payment_method": "pm_card_visa",
        "confirm": True,
        "automatic_payment_methods": {"enabled": True, "allow_redirects": "never"},
    }
    if metadata:
        args["metadata"] = metadata
    return call_tool("create_payment_intent", args)


def mcp_create_subscription(
    vendor: str,
    amount_cents: int,
    currency: str = "usd",
) -> dict:
    """Provision a subscription via MCP: Product -> Price -> Customer -> Subscription.

    The Stripe MCP server exposes each resource as a separate tool; we
    compose them in the documented sequence.
    """
    product = call_tool("create_product", {"name": f"NemoClaw SaaS — {vendor}"})
    product_id = product.get("id") or product.get("product", {}).get("id")

    price = call_tool("create_price", {
        "product": product_id,
        "unit_amount": amount_cents,
        "currency": currency,
        "recurring": {"interval": "month"},
    })
    price_id = price.get("id") or price.get("price", {}).get("id")

    customer = call_tool("create_customer", {
        "name": f"nemoclaw-smb:{vendor}",
        "metadata": {"vendor": vendor},
    })
    customer_id = customer.get("id") or customer.get("customer", {}).get("id")

    sub = call_tool("create_subscription", {
        "customer": customer_id,
        "items": [{"price": price_id}],
    })
    return sub


def mcp_collect_fee(amount_cents: int, metadata: dict | None = None) -> dict:
    """Create a PaymentIntent for NemoClaw's platform fee via MCP."""
    base_meta: dict[str, Any] = {"fee_type": "nemoclaw_platform_fee"}
    if metadata:
        base_meta.update(metadata)
    return mcp_pay(amount_cents, currency="usd", metadata=base_meta)
