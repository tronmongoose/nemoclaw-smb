"""tests/test_str_foundation.py -- Foundation tests for the STR agent scaffold.

Covers:
  - model_routing: no Chinese models, correct tier assignment
  - mock_ledger: prop-001 anomaly present, revenue correct
  - payments/envelopes: sign/verify round-trip; tamper detection
  - c1_governance: issue_nhi returns scoped record; authorize never raises
"""
from __future__ import annotations

import time

import pytest


# ---------------------------------------------------------------------------
# model_routing
# ---------------------------------------------------------------------------

class TestModelRouting:
    """Routing table correctness and Chinese-model ban enforcement."""

    def test_no_chinese_models(self) -> None:
        """MODEL_ROUTING must not reference any Chinese-origin model."""
        from config.model_routing import MODEL_ROUTING, _BANNED_ORIGIN_SUBSTRINGS
        for task, model in MODEL_ROUTING.items():
            lower = model.lower()
            for banned in _BANNED_ORIGIN_SUBSTRINGS:
                assert banned not in lower, (
                    f"Chinese-origin model found: task={task!r} model={model!r}"
                )

    def test_nemotron_tier_tasks(self) -> None:
        """Anomaly, pricing, and AEO tasks must route to Nemotron Ultra."""
        from config.model_routing import NEMOTRON_ULTRA, route_for
        for task in ("anomaly_detection", "dynamic_pricing", "aeo_scoring", "aeo_reasoning"):
            assert route_for(task) == NEMOTRON_ULTRA, f"Expected Nemotron for {task!r}"

    def test_hermes_tier_tasks(self) -> None:
        """Formatting and classification tasks must route to Hermes-small."""
        from config.model_routing import HERMES_SMALL, route_for
        for task in ("listing_format", "guest_message_classify", "expense_categorize"):
            assert route_for(task) == HERMES_SMALL, f"Expected Hermes for {task!r}"

    def test_unknown_task_raises(self) -> None:
        """route_for must raise KeyError for unknown task names."""
        from config.model_routing import route_for
        with pytest.raises(KeyError):
            route_for("nonexistent_task_xyz")

    def test_assert_no_chinese_ran_at_import(self) -> None:
        """The Chinese-model assertion runs at import time; importation must succeed."""
        import config.model_routing  # noqa: F401 -- import triggers the assert
        assert True


# ---------------------------------------------------------------------------
# mock_ledger
# ---------------------------------------------------------------------------

class TestMockLedger:
    """Ledger data correctness, anomaly seeding, and helpers."""

    def test_prop001_anomaly_present(self) -> None:
        """prop-001 charged fee must differ from contracted fee."""
        from data.mock_ledger import MANAGEMENT_FEES_CHARGED, PROPERTIES
        contracted = PROPERTIES["prop-001"]["management_contract_pct"]
        charged = MANAGEMENT_FEES_CHARGED["prop-001"]
        assert charged != contracted, "prop-001 anomaly not seeded"
        assert charged == pytest.approx(0.22)
        assert contracted == pytest.approx(0.20)

    def test_prop001_revenue_cents(self) -> None:
        """prop-001 monthly revenue must equal $4,200 (420000 cents)."""
        from data.mock_ledger import MONTHLY_REVENUE
        assert MONTHLY_REVENUE["prop-001"] == 420000

    def test_get_ledger_summary_anomaly(self) -> None:
        """Ledger summary for prop-001 must flag anomaly=True with positive delta."""
        from data.mock_ledger import get_ledger_summary
        summary = get_ledger_summary("prop-001", "2026-06")
        assert summary["anomaly"] is True
        assert summary["fee_delta_cents"] > 0

    def test_non_anomaly_properties(self) -> None:
        """Properties other than prop-001 must have anomaly=False in their summaries."""
        from data.mock_ledger import get_ledger_summary
        for pid in ("prop-002", "prop-003", "prop-004", "prop-005"):
            summary = get_ledger_summary(pid, "2026-06")
            assert summary["anomaly"] is False, f"{pid} should not be anomalous"

    def test_list_properties_for_owner(self) -> None:
        """Owner-001 must own only prop-001."""
        from data.mock_ledger import list_properties_for_owner
        props = list_properties_for_owner("owner-001")
        assert props == ["prop-001"]

    def test_crew_has_three_members(self) -> None:
        """CREW must have exactly 3 members with correct rates."""
        from data.mock_ledger import CREW
        assert len(CREW) == 3
        rates = {c["name"]: c["rate_cents"] for c in CREW}
        assert rates["Maria S."] == 8500
        assert rates["James T."] == 8500
        assert rates["Falcon Maintenance"] == 15000

    def test_get_property_unknown_raises(self) -> None:
        """get_property must raise KeyError for an unknown property_id."""
        from data.mock_ledger import get_property
        with pytest.raises(KeyError):
            get_property("prop-999")


# ---------------------------------------------------------------------------
# payments/envelopes
# ---------------------------------------------------------------------------

class TestEnvelopes:
    """Ed25519 envelope sign/verify and tamper detection."""

    def test_sign_verify_roundtrip(self) -> None:
        """sign() followed by verify() with the same key must return True."""
        from payments.envelopes import _load_or_generate_key, sign, verify
        priv_hex, pub_hex = _load_or_generate_key()
        payload = {"action": "pay", "vendor": "stripe", "amount_cents": 1000}
        sig = sign(payload, priv_hex)
        assert verify(payload, sig, pub_hex) is True

    def test_tampered_payload_fails_verify(self) -> None:
        """verify() must return False when the payload is modified after signing."""
        from payments.envelopes import _load_or_generate_key, sign, verify
        priv_hex, pub_hex = _load_or_generate_key()
        payload = {"action": "pay", "vendor": "stripe", "amount_cents": 1000}
        sig = sign(payload, priv_hex)
        tampered = {**payload, "amount_cents": 99999}
        assert verify(tampered, sig, pub_hex) is False

    def test_wrong_key_fails_verify(self) -> None:
        """verify() must return False when a different key is used."""
        from payments.envelopes import _load_or_generate_key, sign, verify
        priv_hex, pub_hex = _load_or_generate_key()
        _, other_pub_hex = _load_or_generate_key()
        payload = {"foo": "bar"}
        sig = sign(payload, priv_hex)
        assert verify(payload, sig, other_pub_hex) is False

    def test_sign_stripe_envelope_structure(self, tmp_path) -> None:
        """sign_stripe_envelope must return a dict with signature and public_key_hex."""
        import os
        os.environ["NEMOCLAW_AUDIT_PATH"] = str(tmp_path / "audit.jsonl")
        from payments.envelopes import sign_stripe_envelope, verify_envelope
        envelope = sign_stripe_envelope(
            "payout",
            {"vendor": "stripe", "amount_cents": 500},
            agent_id="str-owner-agent",
            scopes=["stripe:payout"],
        )
        assert "signature" in envelope
        assert "public_key_hex" in envelope
        assert envelope["agent_id"] == "str-owner-agent"
        assert verify_envelope(envelope) is True

    def test_verify_envelope_tamper(self, tmp_path) -> None:
        """verify_envelope must return False when the envelope payload is altered."""
        import os
        os.environ["NEMOCLAW_AUDIT_PATH"] = str(tmp_path / "audit.jsonl")
        from payments.envelopes import sign_stripe_envelope, verify_envelope
        envelope = sign_stripe_envelope(
            "payout",
            {"vendor": "stripe", "amount_cents": 500},
            agent_id="str-owner-agent",
            scopes=["stripe:payout"],
        )
        tampered = {**envelope, "agent_id": "rogue-agent"}
        assert verify_envelope(tampered) is False


# ---------------------------------------------------------------------------
# c1_governance
# ---------------------------------------------------------------------------

class TestC1Governance:
    """ConductorOne governance: NHI issuance and access authorization."""

    def test_issue_nhi_structure(self) -> None:
        """issue_nhi must return a dict with required governance fields."""
        from control_plane.c1_governance import issue_nhi
        nhi = issue_nhi("str-owner-agent", ["stripe:payout", "ledger:read"])
        assert nhi["agent_id"] == "str-owner-agent"
        assert "stripe:payout" in nhi["scopes"]
        assert "ledger:read" in nhi["scopes"]
        assert nhi["status"] == "active"
        assert nhi["governance_source"] == "conductorone-synthetic-demo"
        assert nhi["expiry"] > int(time.time())

    def test_issue_nhi_ttl(self) -> None:
        """issue_nhi expiry must respect the ttl_seconds parameter."""
        from control_plane.c1_governance import issue_nhi
        before = int(time.time())
        nhi = issue_nhi("agent-x", ["read"], ttl_seconds=300)
        assert nhi["expiry"] >= before + 300

    def test_authorize_never_raises(self) -> None:
        """authorize must not raise even when policy_check is unavailable."""
        from control_plane.c1_governance import authorize, issue_nhi
        nhi = issue_nhi("test-agent", ["ledger:read"])
        # Should not raise regardless of policy backend state.
        allowed, reason = authorize(nhi, "read", "ledger")
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)

    def test_authorize_returns_tuple(self) -> None:
        """authorize must return a (bool, str) tuple."""
        from control_plane.c1_governance import authorize, issue_nhi
        nhi = issue_nhi("test-agent", ["stripe:payout"])
        result = authorize(nhi, "payout", "stripe")
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
