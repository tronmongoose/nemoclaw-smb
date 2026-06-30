"""demo/run_demo.py: Three-act console demo runner for the STR agent.

Orchestrates all three acts in sequence using real act functions. DEMO_MODE
must be set (default: true) so no live credentials are required.

Run with: python -m demo.run_demo

Public API:
    run_act_1() -> None: STR Owner: ledger, anomaly, approval gate, payment
    run_act_2() -> None: Property Mgmt: checkout, card, payouts, UBP invoice
    run_act_3() -> None: Platform: MPP 402/200 loop, AEO audit, earn metrics
    run_demo()  -> None: Runs all three acts then prints audit chain verification
"""
from __future__ import annotations

import json
import os

# Ensure DEMO_MODE is active before any import triggers side-effects.
os.environ.setdefault("DEMO_MODE", "true")

from acts.platform_agent import get_metrics, reset_metrics, serve_aeo_call, serve_pricing_call
from acts.property_mgmt_agent import (
    calculate_ubp_invoices,
    get_portfolio_summary,
    handle_checkout_event,
    run_month_end_payouts,
)
from acts.str_owner_agent import reconcile_month
from agent.audit_log import verify_chain
from config.model_routing import HERMES_SMALL, NEMOTRON_ULTRA
from data.mock_listings import LISTINGS
from payments.mpp_server import app as _mpp_app  # noqa: F401 (drives TestClient)
from demo._act_helpers import (
    pause_for_narration,
    print_act_header,
    show_anomaly_catch,
    show_aeo_breakdown,
    show_audit_tail,
    show_card_result,
    show_ledger_table,
    show_metrics,
    show_mpp_exchange,
    show_nhi,
    show_approval_hold,
    show_payment_result,
    show_payout_batch,
    show_ubp_invoice,
)

_DEMO_PROPERTY = "prop-001"
_DEMO_MONTH = "2026-05"
_DEMO_CHECKOUT_DATE = "2026-05-31"
_CLEMENTINE_LISTING_URL = "https://www.airbnb.com/rooms/838634728141757030"


# ---------------------------------------------------------------------------
# Act 1: I'm a Property Owner
# ---------------------------------------------------------------------------

def _show_act1_ledger_and_anomaly(report: object) -> None:
    """Display the 30-day ledger summary and anomaly detection result."""
    pause_for_narration("Loading the Sweet Clementine 30-day ledger...")
    show_ledger_table(report.summary)
    pause_for_narration("Running anomaly detection (Nemotron Ultra)...")
    show_anomaly_catch(report.anomaly)


def _show_act1_governance(report: object) -> None:
    """Display the C1 NHI and the REQUIRE_APPROVAL hold."""
    from acts.str_owner_agent import _NHI  # noqa: PLC2701
    pause_for_narration("ConductorOne NHI the agent runs under:")
    show_nhi(report.nhi_id, _NHI["scopes"], label="str-owner-agent NHI")
    if report.anomaly.is_anomaly:
        show_approval_hold(report.anomaly.expected_fee_cents)


def _show_act1_payment(report: object) -> None:
    """Display the signed corrected payment and audit tail."""
    if report.payment:
        pause_for_narration("Simulating approval... payment released.")
        show_payment_result(report.payment)
    ok, detail = verify_chain()
    pause_for_narration("Audit log tail:")
    show_audit_tail(ok, detail)


def run_act_1() -> None:
    """ACT 1: I'm a Property Owner.

    Loads the Sweet Clementine ledger, detects the $924 vs $840 overcharge,
    shows the C1 NHI, demonstrates REQUIRE_APPROVAL holding the corrected $840,
    simulates approval, and shows the signed payment plus audit chain tail.
    """
    print_act_header("I'M A PROPERTY OWNER")
    pause_for_narration(f"Model routing: heavy tasks -> {NEMOTRON_ULTRA}")
    #COMPLETION_DRIVE: reconcile_month runs the full Act I flow including demo auto-approval
    report = reconcile_month(_DEMO_PROPERTY, _DEMO_MONTH)
    _show_act1_ledger_and_anomaly(report)
    _show_act1_governance(report)
    _show_act1_payment(report)


# ---------------------------------------------------------------------------
# Act 2: I'm the Management Company
# ---------------------------------------------------------------------------

def _show_act2_checkout(card_result: object) -> None:
    """Display checkout event, cleaner NHI, and card issuance."""
    pause_for_narration(
        f"Guest checks out of {_DEMO_PROPERTY} on {_DEMO_CHECKOUT_DATE}. "
        "Issuing cleaner card..."
    )
    show_nhi(
        f"nhi-cleaner-subagent-*",
        ["card:issue:cleaning"],
        label="Cleaner sub-agent NHI (least-privilege, 1h TTL)",
    )
    show_card_result(card_result)


def _show_act2_payouts(batch: object, invoices: list) -> None:
    """Display month-end payouts and per-owner UBP invoices."""
    pause_for_narration("Running month-end Global Payouts for 3 crew members...")
    show_payout_batch(batch)
    pause_for_narration("Calculating UBP invoices per owner...")
    for inv in invoices:
        show_ubp_invoice(inv)


def run_act_2() -> None:
    """ACT 2: I'm the Management Company.

    Simulates a checkout event, shows the cleaner sub-agent getting a
    least-privilege C1 NHI, issues a single-use card (token only, $75 cap,
    MCC 7349/5251, EOD expiry), runs month-end payouts to 3 crew, and shows
    per-owner UBP invoices.
    """
    print_act_header("I'M THE MANAGEMENT COMPANY")
    pause_for_narration(f"Model routing: small/format tasks -> {HERMES_SMALL}")
    card = handle_checkout_event(_DEMO_PROPERTY, _DEMO_CHECKOUT_DATE)
    _show_act2_checkout(card)
    batch = run_month_end_payouts(_DEMO_MONTH)
    invoices = calculate_ubp_invoices(_DEMO_MONTH)
    _show_act2_payouts(batch, invoices)


# ---------------------------------------------------------------------------
# Act 3: I'm the Platform
# ---------------------------------------------------------------------------

def _mpp_price_roundtrip() -> dict:
    """Drive the MPP /price endpoint: 402 first, then 200 with token."""
    from fastapi.testclient import TestClient
    from payments.mpp_server import app

    client = TestClient(app, raise_server_exceptions=True)
    body = {
        "property_id": _DEMO_PROPERTY,
        "current_rate": 185.0,
        "occupancy_rate": 0.74,
        "local_events": ["Oceanside airshow"],
        "comp_set_rates": [175.0, 195.0, 182.0],
        "season": "shoulder",
        "day_of_week": "sat",
    }
    # Step 1: no token -> 402
    r402 = client.post("/price", json=body)
    show_mpp_exchange(r402.status_code, r402.json(), "no token -> 402 Payment Required")
    # Step 2: valid token -> 200
    r200 = client.post("/price", json=body, headers={"Authorization": "Bearer mpp_tok_demo"})
    return {"status_402": r402.status_code, "status_200": r200.status_code, "result": r200.json()}


def _mpp_aeo_roundtrip() -> dict:
    """Drive the MPP /aeo-audit endpoint: 402 first, then 200 with token."""
    from fastapi.testclient import TestClient
    from payments.mpp_server import app

    client = TestClient(app, raise_server_exceptions=True)
    listing = LISTINGS["prop-001"]
    body = {
        "listing_text": listing["description"],
        "amenities_list": listing.get("amenities", []),
        "existing_schema": {},
        "listing_url": _CLEMENTINE_LISTING_URL,
    }
    r402 = client.post("/aeo-audit", json=body)
    show_mpp_exchange(r402.status_code, r402.json(), "no token -> 402 Payment Required")
    r200 = client.post("/aeo-audit", json=body, headers={"Authorization": "Bearer mpp_tok_demo"})
    return {"status_402": r402.status_code, "status_200": r200.status_code, "result": r200.json()}


def _show_act3_pricing(price_data: dict) -> None:
    """Display the pricing recommendation from the 200 response."""
    pause_for_narration("MPP /price: 200 OK with earn event:")
    r200_body = price_data["result"]
    show_mpp_exchange(price_data["status_200"], {
        "service": r200_body.get("service"),
        "amount_cents": r200_body.get("amount_cents"),
        "recommended_rate": r200_body["result"]["recommended_rate"],
        "confidence": r200_body["result"]["confidence"],
        "reasoning": r200_body["result"]["reasoning"],
    }, "valid token -> 200 OK")


def _show_act3_aeo(aeo_data: dict) -> None:
    """Display the full AEO audit from the 200 response plus the serve_aeo_call result."""
    pause_for_narration("MPP /aeo-audit: 200 OK. Running full AEO audit...")
    listing = LISTINGS["prop-001"]
    aeo_full = serve_aeo_call(
        listing_text=listing["description"],
        amenities_list=listing.get("amenities", []),
        listing_url=_CLEMENTINE_LISTING_URL,
    )
    # Reconstruct an object-like namespace for show_aeo_breakdown
    from skills.aeo_skill import audit_listing, AEOAuditRequest
    req = AEOAuditRequest(
        listing_text=listing["description"],
        amenities_list=listing.get("amenities", []),
        existing_schema={},
        listing_url=_CLEMENTINE_LISTING_URL,
    )
    aeo_result = audit_listing(req)
    show_aeo_breakdown(aeo_result)


def run_act_3() -> None:
    """ACT 3: I'm the Platform.

    Calls MPP /price via TestClient showing 402 then 200-with-token (the 402
    loop is the point), shows the pricing recommendation and reasoning, calls
    /aeo-audit (402 then 200), shows the full AEO audit for Sweet Clementine
    (51/100 breakdown, CRITICAL dog-only conflict, optimized opening, JSON-LD
    schema), and shows platform earn metrics plus mpp_earn audit events.
    """
    print_act_header("I'M THE PLATFORM")
    reset_metrics()
    # Pricing roundtrip: 402 -> 200
    pause_for_narration("Calling POST /price without a token to show the 402 gate...")
    price_data = _mpp_price_roundtrip()
    _show_act3_pricing(price_data)
    # AEO roundtrip: 402 -> 200
    pause_for_narration("Calling POST /aeo-audit without a token to show the 402 gate...")
    aeo_data = _mpp_aeo_roundtrip()
    _show_act3_aeo(aeo_data)
    # Earn metrics
    pause_for_narration("Platform earn metrics after this session:")
    show_metrics(get_metrics())
    pause_for_narration("mpp_earn audit events written to hash-chained log.")
    ok, detail = verify_chain()
    show_audit_tail(ok, detail)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def run_demo() -> None:
    """Run all three acts then print the final audit chain verification."""
    run_act_1()
    run_act_2()
    run_act_3()
    print_act_header("FINAL AUDIT CHAIN VERIFICATION")
    ok, detail = verify_chain()
    show_audit_tail(ok, detail)
    if not ok:
        raise RuntimeError(f"Audit chain failed: {detail}")


if __name__ == "__main__":
    run_demo()
