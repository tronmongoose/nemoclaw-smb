"""
Tests for payments/stripe_mcp.py and MCP routing in payments/stripe_client.py.

Coverage:
- stripe_mcp_enabled() returns True/False based on env + npx presence.
- call_tool routes through the MCP session (monkeypatched, no subprocess/network).
- stripe_client.pay routes to backend="mcp" when enabled.
- stripe_client.pay falls back to backend="sdk" when MCP raises + key present.
- stripe_client.pay falls back to backend="mock" with no key.
- stripe_client.create_subscription and collect_fee follow the same order.
- Amounts are always in cents when passed to MCP helpers.
"""

import importlib
import sys
import types
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stripe_stub(pi_id="pi_sdk_001", sub_id="sub_sdk_002",
                      prod_id="prod_xxx", price_id="price_yyy", cust_id="cus_zzz"):
    """Minimal stripe SDK stub (same shape as test_stripe_client.py)."""

    class _Obj:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    stub = types.SimpleNamespace()
    calls: dict = {}

    class PaymentIntentStub:
        @staticmethod
        def create(**params):
            calls["payment_intent_create"] = params
            return _Obj(id=pi_id, status="succeeded")

    class ProductStub:
        @staticmethod
        def create(**params):
            calls["product_create"] = params
            return _Obj(id=prod_id)

    class PriceStub:
        @staticmethod
        def create(**params):
            calls["price_create"] = params
            return _Obj(id=price_id)

    class CustomerStub:
        @staticmethod
        def create(**params):
            calls["customer_create"] = params
            return _Obj(id=cust_id)

    class SubscriptionStub:
        @staticmethod
        def create(**params):
            calls["subscription_create"] = params
            return _Obj(id=sub_id, status="active")

    stub.PaymentIntent = PaymentIntentStub
    stub.Product = ProductStub
    stub.Price = PriceStub
    stub.Customer = CustomerStub
    stub.Subscription = SubscriptionStub
    stub.api_key = None
    stub._calls = calls
    return stub


def _fake_call_tool(name, arguments):
    """Fake MCP call_tool: returns canned ids without touching subprocess."""
    if name == "create_payment_intent":
        return {"id": "pi_mcp_fake_001", "status": "succeeded"}
    if name == "create_product":
        return {"id": "prod_mcp_fake"}
    if name == "create_price":
        return {"id": "price_mcp_fake"}
    if name == "create_customer":
        return {"id": "cus_mcp_fake"}
    if name == "create_subscription":
        return {"id": "sub_mcp_fake_001", "status": "active"}
    return {"id": f"mcp_fake_{name}"}


# ---------------------------------------------------------------------------
# stripe_mcp_enabled() tests
# ---------------------------------------------------------------------------

class TestStripeMcpEnabled:
    def test_disabled_by_force_sdk_flag(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
        monkeypatch.setenv("STRIPE_FORCE_SDK", "1")
        from payments import stripe_mcp
        importlib.reload(stripe_mcp)
        assert stripe_mcp.stripe_mcp_enabled() is False

    def test_disabled_without_test_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        from payments import stripe_mcp
        importlib.reload(stripe_mcp)
        assert stripe_mcp.stripe_mcp_enabled() is False

    def test_disabled_with_live_key(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_bad")
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        from payments import stripe_mcp
        importlib.reload(stripe_mcp)
        assert stripe_mcp.stripe_mcp_enabled() is False

    def test_enabled_with_test_key_and_npx(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        # Patch shutil.which to return a path for npx
        import shutil
        monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/npx" if cmd == "npx" else None)
        from payments import stripe_mcp
        importlib.reload(stripe_mcp)
        assert stripe_mcp.stripe_mcp_enabled() is True

    def test_disabled_when_npx_missing(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        import shutil
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        from payments import stripe_mcp
        importlib.reload(stripe_mcp)
        assert stripe_mcp.stripe_mcp_enabled() is False


# ---------------------------------------------------------------------------
# stripe_client routing: MCP path
# ---------------------------------------------------------------------------

class TestStripeClientMcpRouting:
    """MCP path exercises via monkeypatched call_tool — no subprocess, no network."""

    def _enable_mcp(self, monkeypatch):
        """Set env and monkeypatch call_tool + stripe_mcp_enabled."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)

    def test_pay_routes_to_mcp_backend(self, monkeypatch):
        self._enable_mcp(monkeypatch)
        from payments import stripe_mcp
        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _fake_call_tool)
        from payments import stripe_client
        importlib.reload(stripe_client)
        result = stripe_client.pay("AWS", 100.0, idempotency_key="test-mcp-1")
        assert result["backend"] == "mcp"
        assert result["id"] == "pi_mcp_fake_001"
        assert result["amount"] == 100.0
        assert result["livemode"] is False

    def test_pay_amounts_in_cents_to_mcp(self, monkeypatch):
        """Verify mcp_pay receives cents, not dollars."""
        self._enable_mcp(monkeypatch)
        recorded: dict = {}

        def _recording_call_tool(name, arguments):
            recorded[name] = arguments
            return {"id": "pi_mcp_amt_check", "status": "succeeded"}

        from payments import stripe_mcp
        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _recording_call_tool)
        from payments import stripe_client
        importlib.reload(stripe_client)
        stripe_client.pay("acme", 312.00)
        assert "create_payment_intent" in recorded
        assert recorded["create_payment_intent"]["amount"] == 31200  # cents

    def test_create_subscription_routes_to_mcp(self, monkeypatch):
        self._enable_mcp(monkeypatch)
        from payments import stripe_mcp
        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _fake_call_tool)
        from payments import stripe_client
        importlib.reload(stripe_client)
        result = stripe_client.create_subscription("Notion", 16.00)
        assert result["backend"] == "mcp"
        assert result["id"] == "sub_mcp_fake_001"
        assert result["status"] == "active"

    def test_create_subscription_amounts_in_cents(self, monkeypatch):
        self._enable_mcp(monkeypatch)
        recorded: dict = {}

        def _rec(name, arguments):
            recorded[name] = arguments
            return _fake_call_tool(name, arguments)

        from payments import stripe_mcp
        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _rec)
        from payments import stripe_client
        importlib.reload(stripe_client)
        stripe_client.create_subscription("Notion", 16.00)
        assert recorded["create_price"]["unit_amount"] == 1600  # cents

    def test_collect_fee_routes_to_mcp(self, monkeypatch):
        self._enable_mcp(monkeypatch)
        from payments import stripe_mcp
        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _fake_call_tool)
        from payments import stripe_client
        importlib.reload(stripe_client)
        result = stripe_client.collect_fee(1.56, "test_basis")
        assert result["backend"] == "mcp"
        assert result["amount"] == 1.56

    def test_collect_fee_amounts_in_cents(self, monkeypatch):
        self._enable_mcp(monkeypatch)
        recorded: dict = {}

        def _rec(name, arguments):
            recorded[name] = arguments
            return {"id": "pi_fee_check", "status": "succeeded"}

        from payments import stripe_mcp
        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _rec)
        from payments import stripe_client
        importlib.reload(stripe_client)
        stripe_client.collect_fee(1.56, "basis_check")
        assert recorded["create_payment_intent"]["amount"] == 156  # cents


# ---------------------------------------------------------------------------
# stripe_client routing: MCP error -> SDK fallback
# ---------------------------------------------------------------------------

class TestStripeClientMcpFallback:
    """When MCP raises StripeMcpError, client must fall back to SDK path."""

    def test_pay_falls_back_to_sdk_on_mcp_error(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        stub = _make_stripe_stub(pi_id="pi_sdk_fallback_001")
        sys.modules["stripe"] = stub

        from payments import stripe_mcp
        from payments.stripe_mcp import StripeMcpError

        def _raising_call_tool(name, arguments):
            raise StripeMcpError("mcp down")

        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _raising_call_tool)

        try:
            from payments import stripe_client
            importlib.reload(stripe_client)
            result = stripe_client.pay("AWS", 100.0)
            assert result["backend"] == "sdk"
            assert result["id"] == "pi_sdk_fallback_001"
        finally:
            if "stripe" in sys.modules and sys.modules["stripe"] is stub:
                del sys.modules["stripe"]

    def test_create_subscription_falls_back_to_sdk_on_mcp_error(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        stub = _make_stripe_stub(sub_id="sub_sdk_fallback_002")
        sys.modules["stripe"] = stub

        from payments import stripe_mcp
        from payments.stripe_mcp import StripeMcpError

        def _raising_call_tool(name, arguments):
            raise StripeMcpError("mcp down")

        monkeypatch.setattr(stripe_mcp, "stripe_mcp_enabled", lambda: True)
        monkeypatch.setattr(stripe_mcp, "call_tool", _raising_call_tool)

        try:
            from payments import stripe_client
            importlib.reload(stripe_client)
            result = stripe_client.create_subscription("Notion", 16.00)
            assert result["backend"] == "sdk"
            assert result["id"] == "sub_sdk_fallback_002"
        finally:
            if "stripe" in sys.modules and sys.modules["stripe"] is stub:
                del sys.modules["stripe"]


# ---------------------------------------------------------------------------
# stripe_client routing: no key -> mock
# ---------------------------------------------------------------------------

class TestStripeClientMockFallback:
    def test_pay_falls_back_to_mock_with_no_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        from payments import stripe_client
        importlib.reload(stripe_client)
        result = stripe_client.pay("acme", 100.0)
        assert result["backend"] == "mock"
        assert result["id"].startswith("pi_test_")

    def test_create_subscription_falls_back_to_mock_with_no_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        from payments import stripe_client
        importlib.reload(stripe_client)
        result = stripe_client.create_subscription("acme", 99.0)
        assert result["backend"] == "mock"
        assert result["id"].startswith("sub_test_")

    def test_collect_fee_falls_back_to_mock_with_no_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_FORCE_SDK", raising=False)
        from payments import stripe_client
        importlib.reload(stripe_client)
        result = stripe_client.collect_fee(1.50, "test_basis")
        assert result["backend"] == "mock"
        assert result["id"].startswith("pi_test_")
