"""
Tests for payments/stripe_client.py.

Coverage:
- No key -> mock id returned, callers not raised-to (existing behavior preserved).
- sk_live_ key -> refused, mock fallback, warning logged.
- sk_test_ key present -> live branch exercised via monkeypatched stripe module;
  asserts SDK called with cents/usd params and returned id surfaces correctly.
- All existing public function signatures preserved.
"""

import types
import logging
import pytest


# ---------------------------------------------------------------------------
# Helpers: minimal stripe SDK stub
# ---------------------------------------------------------------------------

def _make_stripe_stub(pi_id="pi_real_abc123", sub_id="sub_real_def456",
                      prod_id="prod_xxx", price_id="price_yyy", cust_id="cus_zzz"):
    """Return a stub stripe module that records calls and returns canned objects."""

    class _Obj:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    stripe_stub = types.SimpleNamespace()

    # Track calls for assertion
    calls = {}

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

    stripe_stub.PaymentIntent = PaymentIntentStub
    stripe_stub.Product = ProductStub
    stripe_stub.Price = PriceStub
    stripe_stub.Customer = CustomerStub
    stripe_stub.Subscription = SubscriptionStub
    stripe_stub.api_key = None
    stripe_stub._calls = calls
    return stripe_stub


# ---------------------------------------------------------------------------
# No-key (mock) behavior
# ---------------------------------------------------------------------------

class TestNoKeyMockBehavior:
    def test_pay_returns_dict_with_id(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from payments import stripe_client
        result = stripe_client.pay("acme", 100.0, idempotency_key="test-1")
        assert result["id"].startswith("pi_test_")
        assert result["status"] == "succeeded"
        assert result["livemode"] is False
        assert result["amount"] == 100.0

    def test_cancel_subscription_returns_canceled(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from payments import stripe_client
        result = stripe_client.cancel_subscription("acme")
        assert result["id"].startswith("sub_test_")
        assert result["status"] == "canceled"

    def test_create_subscription_returns_active(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from payments import stripe_client
        result = stripe_client.create_subscription("acme", 299.0)
        assert result["id"].startswith("sub_test_")
        assert result["status"] == "active"
        assert result["amount"] == 299.0

    def test_collect_fee_returns_succeeded(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from payments import stripe_client
        result = stripe_client.collect_fee(1.50, "demo_run_spend_$300.00")
        assert result["id"].startswith("pi_test_")
        assert result["status"] == "succeeded"
        assert result["amount"] == 1.50

    def test_pay_idempotent_same_key(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from payments import stripe_client
        r1 = stripe_client.pay("acme", 100.0, idempotency_key="k1")
        r2 = stripe_client.pay("acme", 100.0, idempotency_key="k1")
        assert r1["id"] == r2["id"]

    def test_pay_different_keys_different_ids(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        from payments import stripe_client
        r1 = stripe_client.pay("acme", 100.0, idempotency_key="k1")
        r2 = stripe_client.pay("acme", 100.0, idempotency_key="k2")
        assert r1["id"] != r2["id"]


# ---------------------------------------------------------------------------
# Live-key refusal (sk_live_ must never be accepted)
# ---------------------------------------------------------------------------

class TestLiveKeyRefused:
    def test_pay_refuses_live_key(self, monkeypatch, caplog):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_definitely_not_allowed")
        from payments import stripe_client
        import importlib
        importlib.reload(stripe_client)
        with caplog.at_level(logging.WARNING, logger="payments.stripe_client"):
            result = stripe_client.pay("acme", 100.0)
        assert result["id"].startswith("pi_test_")
        assert any("live-mode" in r.message or "sk_live_" in r.message
                   for r in caplog.records)

    def test_create_subscription_refuses_live_key(self, monkeypatch, caplog):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_bad_key")
        from payments import stripe_client
        import importlib
        importlib.reload(stripe_client)
        with caplog.at_level(logging.WARNING, logger="payments.stripe_client"):
            result = stripe_client.create_subscription("acme", 99.0)
        assert result["id"].startswith("sub_test_")

    def test_collect_fee_refuses_live_key(self, monkeypatch, caplog):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_bad_key")
        from payments import stripe_client
        import importlib
        importlib.reload(stripe_client)
        with caplog.at_level(logging.WARNING, logger="payments.stripe_client"):
            result = stripe_client.collect_fee(5.00, "test_basis")
        assert result["id"].startswith("pi_test_")


# ---------------------------------------------------------------------------
# Live branch (sk_test_ key) — monkeypatched stripe module, no network
# ---------------------------------------------------------------------------

class TestLiveBranchMonkeypatched:
    """Exercise the real branch with a fake sk_test_ key and a stub stripe module."""

    def _patch(self, monkeypatch, stub):
        """Set env key and patch the stripe import inside _get_stripe."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key_for_testing")
        import sys
        sys.modules["stripe"] = stub
        yield
        # cleanup: remove stub so other tests get the real module
        if "stripe" in sys.modules and sys.modules["stripe"] is stub:
            del sys.modules["stripe"]

    def test_pay_calls_payment_intent_create(self, monkeypatch):
        stub = _make_stripe_stub(pi_id="pi_real_test_001")
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        import sys
        sys.modules["stripe"] = stub
        try:
            from payments import stripe_client
            import importlib
            importlib.reload(stripe_client)
            result = stripe_client.pay("AWS", 312.00, idempotency_key="inv-aws-001")
            # SDK must be called with cents and usd
            assert "payment_intent_create" in stub._calls
            params = stub._calls["payment_intent_create"]
            assert params["amount"] == 31200  # $312 -> 31200 cents
            assert params["currency"] == "usd"
            assert params["confirm"] is True
            # Returned id must be the real Stripe id, not a mock hash
            assert result["id"] == "pi_real_test_001"
            assert result["livemode"] is False
        finally:
            del sys.modules["stripe"]

    def test_create_subscription_calls_product_price_subscription(self, monkeypatch):
        stub = _make_stripe_stub(sub_id="sub_real_test_002")
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        import sys
        sys.modules["stripe"] = stub
        try:
            from payments import stripe_client
            import importlib
            importlib.reload(stripe_client)
            result = stripe_client.create_subscription("Notion", 16.00)
            # Product must be created
            assert "product_create" in stub._calls
            # Price must be created with cents and recurring monthly
            assert "price_create" in stub._calls
            price_params = stub._calls["price_create"]
            assert price_params["unit_amount"] == 1600  # $16 -> 1600 cents
            assert price_params["currency"] == "usd"
            assert price_params["recurring"]["interval"] == "month"
            # Subscription must be created
            assert "subscription_create" in stub._calls
            assert result["id"] == "sub_real_test_002"
            assert result["status"] == "active"
        finally:
            del sys.modules["stripe"]

    def test_collect_fee_calls_payment_intent_create(self, monkeypatch):
        stub = _make_stripe_stub(pi_id="pi_real_fee_003")
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        import sys
        sys.modules["stripe"] = stub
        try:
            from payments import stripe_client
            import importlib
            importlib.reload(stripe_client)
            result = stripe_client.collect_fee(1.56, "demo_spend_$312")
            assert "payment_intent_create" in stub._calls
            params = stub._calls["payment_intent_create"]
            assert params["amount"] == 156  # $1.56 -> 156 cents
            assert params["currency"] == "usd"
            assert result["id"] == "pi_real_fee_003"
        finally:
            del sys.modules["stripe"]

    def test_pay_falls_back_on_stripe_error(self, monkeypatch):
        """When the stripe SDK raises, mock path must be returned (no raise)."""
        stub = _make_stripe_stub()

        class _Failing:
            @staticmethod
            def create(**params):
                raise RuntimeError("network error")

        stub.PaymentIntent = _Failing
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        import sys
        sys.modules["stripe"] = stub
        try:
            from payments import stripe_client
            import importlib
            importlib.reload(stripe_client)
            result = stripe_client.pay("AWS", 100.0)
            # Must not raise; must return mock id
            assert result["id"].startswith("pi_test_")
        finally:
            del sys.modules["stripe"]

    def test_create_subscription_falls_back_on_stripe_error(self, monkeypatch):
        stub = _make_stripe_stub()

        class _Failing:
            @staticmethod
            def create(**params):
                raise RuntimeError("network error")

        stub.Product = _Failing
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
        import sys
        sys.modules["stripe"] = stub
        try:
            from payments import stripe_client
            import importlib
            importlib.reload(stripe_client)
            result = stripe_client.create_subscription("Notion", 16.00)
            assert result["id"].startswith("sub_test_")
        finally:
            del sys.modules["stripe"]
