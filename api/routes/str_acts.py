"""api/routes/str_acts.py: HTTP surface over the three STR agent acts.

Exposes the act orchestrators so a web UI can render Act I (owner-fee
reconciliation), Act II (property-management orchestration), and Act III
(platform earn server) over HTTP. Every read/serve endpoint accepts a `live`
query param (default false) threaded straight through to the act function, so
the UI can flip between deterministic demo traces and real Nemotron reasoning.

Returned dataclasses are serialized to JSON via dataclasses.asdict, preserving
reasoning provenance (mode, model, latency_ms, source) on Act I anomalies.

Exports (via router):
    GET  /str/act1/{property_id}/{month}      reconcile_month
    POST /str/act2/checkout                   handle_checkout_event
    GET  /str/act2/payouts/{month}           run_month_end_payouts
    GET  /str/act2/invoices/{month}          calculate_ubp_invoices
    GET  /str/act2/portfolio                  get_portfolio_summary
    POST /str/act3/price                      serve_pricing_call
    POST /str/act3/aeo-audit                  402-then-200 earn call
    GET  /str/act3/metrics                    get_metrics
    GET  /str/audit                           STR-scoped audit + verify_chain
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import List, Optional  # noqa: UP035 (3.9 FastAPI/Pydantic needs typing generics)

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from acts.platform_agent import get_metrics, serve_aeo_call, serve_pricing_call
from acts.property_mgmt_agent import (
    calculate_ubp_invoices,
    get_portfolio_summary,
    handle_checkout_event,
    run_month_end_payouts,
)
from acts.str_owner_agent import reconcile_month
from agent.audit_log import verify_chain
from agent.interactions_log import read_interactions
from agent.interactions_log import verify_chain as verify_interactions
from api.seed import DEMO_AUDIT_PATH, DEMO_INTERACTIONS_PATH
from payments.mpp_server import (
    AEO_AUDIT_ENDPOINT_CENTS,
    _extract_token,
    validate_mpp_token,
)

router = APIRouter(prefix="/str", tags=["str-acts"])

# Earn events and act payments write to the shared demo audit chain so /str/audit
# can read them back and verify integrity end to end.
_AUDIT_PATH_STR: str = str(DEMO_AUDIT_PATH)

# audit "actor" / token-id substrings that mark an entry as STR-scoped.
_STR_ACTORS = frozenset({"str-owner-agent", "cleaner-subagent", "property-mgmt-agent"})
_STR_SERVICES = frozenset({"price", "aeo-audit"})


# ---------------------------------------------------------------------------
# Pydantic request bodies (3.9-safe: typing.List/Optional, never PEP-604 pipe)
# ---------------------------------------------------------------------------


class CheckoutBody(BaseModel):
    """Request body for POST /str/act2/checkout."""

    property_id: str
    checkout_date: str


class PriceBody(BaseModel):
    """Request body for POST /str/act3/price."""

    property_id: str
    current_rate: float
    occupancy_rate: float
    local_events: List[str] = []  # noqa: UP006 (3.9 Pydantic field)
    comp_set_rates: List[float] = []  # noqa: UP006 (3.9 Pydantic field)
    season: str = "shoulder"
    day_of_week: str = "sat"


class AEOBody(BaseModel):
    """Request body for POST /str/act3/aeo-audit."""

    listing_text: str
    amenities_list: List[str] = []  # noqa: UP006 (3.9 Pydantic field)
    existing_schema: dict = {}
    listing_url: str = ""


# ---------------------------------------------------------------------------
# Act I: owner-fee reconciliation
# ---------------------------------------------------------------------------


@router.get("/act1/{property_id}/{month}")
def act1_reconcile(
    property_id: str,
    month: str,
    live: bool = Query(default=False),
) -> dict:
    """Run Act I reconciliation; serialize the full report incl. provenance.

    The `anomaly` block carries reasoning_provenance (mode, model, latency_ms,
    source). `live` is threaded through to detect_fee_anomaly's reasoning path.
    """
    report = reconcile_month(property_id, month, live=live)
    return asdict(report)


# ---------------------------------------------------------------------------
# Act II: property-management orchestration
# ---------------------------------------------------------------------------


@router.post("/act2/checkout")
def act2_checkout(body: CheckoutBody) -> dict:
    """Issue a single-use cleaner card on guest checkout (Act II)."""
    result = handle_checkout_event(body.property_id, body.checkout_date)
    return asdict(result)


@router.get("/act2/payouts/{month}")
def act2_payouts(month: str) -> dict:
    """Run month-end crew payouts for the given month (Act II)."""
    batch = run_month_end_payouts(month)
    return asdict(batch)


@router.get("/act2/invoices/{month}")
def act2_invoices(month: str) -> dict:
    """Return UBP owner invoices for the given month (Act II)."""
    invoices = calculate_ubp_invoices(month)
    return {"month": month, "invoices": [asdict(inv) for inv in invoices]}


@router.get("/act2/portfolio")
def act2_portfolio() -> dict:
    """Return the portfolio summary across all managed properties (Act II)."""
    return asdict(get_portfolio_summary())


# ---------------------------------------------------------------------------
# Act III: platform earn server
# ---------------------------------------------------------------------------


@router.post("/act3/price")
def act3_price(
    body: PriceBody,
    live: bool = Query(default=False),
    authorization: Optional[str] = Header(default=None),  # noqa: UP045 (3.9 route sig)
) -> dict:
    """Serve a pricing call through Act III and log the earn event.

    An optional Authorization bearer token selects the demo token; absent or
    malformed headers fall back to the platform default. `live` threads to the
    pricing reasoning so a real Nemotron call fires when a key is present.
    """
    token = _extract_token(authorization) or "mpp_tok_demo"
    return serve_pricing_call(
        property_id=body.property_id,
        current_rate=body.current_rate,
        occupancy_rate=body.occupancy_rate,
        local_events=body.local_events,
        comp_set_rates=body.comp_set_rates,
        season=body.season,
        day_of_week=body.day_of_week,
        demo_token=token,
        audit_path=_AUDIT_PATH_STR,
        live=live,
    )


@router.post("/act3/aeo-audit")
def act3_aeo_audit(
    body: AEOBody,
    live: bool = Query(default=False),
    authorization: Optional[str] = Header(default=None),  # noqa: UP045 (3.9 route sig)
):
    """The real 402-then-200 earn loop: no token -> 402, mpp_tok_ token -> 200.

    Returns a JSONResponse with status 402 (and the Stripe-MPP WWW-Authenticate
    header) when no valid token is present, else serves the AEO audit and logs
    the earn event. `live` threads to the AEO reasoning so a real Nemotron call
    fires when a key is present.
    """
    token = _extract_token(authorization)
    if not token or not validate_mpp_token(token):
        amount_dollars = AEO_AUDIT_ENDPOINT_CENTS / 100
        return JSONResponse(
            status_code=402,
            content={"error": "payment_required", "amount_cents": AEO_AUDIT_ENDPOINT_CENTS},
            headers={
                "WWW-Authenticate": f"stripe-mpp charge=${amount_dollars:.2f} currency=usd"
            },
        )
    return serve_aeo_call(
        listing_text=body.listing_text,
        amenities_list=body.amenities_list,
        existing_schema=body.existing_schema,
        listing_url=body.listing_url,
        demo_token=token,
        audit_path=_AUDIT_PATH_STR,
        live=live,
    )


@router.get("/act3/metrics")
def act3_metrics() -> dict:
    """Return platform-level Act III metrics (calls served, revenue, properties)."""
    return get_metrics()


# ---------------------------------------------------------------------------
# STR-scoped audit read + chain verification
# ---------------------------------------------------------------------------


def _is_str_entry(entry: dict) -> bool:
    """Return True when an audit entry belongs to an STR act or earn event."""
    if entry.get("event") == "mpp_earn":
        return entry.get("service") in _STR_SERVICES
    if entry.get("actor") in _STR_ACTORS:
        return True
    return entry.get("vendor", "").startswith(("stripe-issuing", "stripe-payouts"))


@router.get("/audit")
def str_audit(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    """Return STR-scoped audit entries (newest last) plus chain verification.

    verify_chain runs over the whole demo chain (not just the STR slice) so the
    hash-chain result reflects true tamper-evidence, not a filtered view.
    """
    entries: list = []
    if DEMO_AUDIT_PATH.exists():
        with DEMO_AUDIT_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if _is_str_entry(parsed):
                    entries.append(parsed)

    entries = entries[-limit:]
    ok, message = verify_chain(path=_AUDIT_PATH_STR)
    return {
        "count": len(entries),
        "entries": entries,
        "verify": {"ok": ok, "message": message},
    }


_INTERACTIONS_PATH_STR: str = str(DEMO_INTERACTIONS_PATH)


@router.get("/interactions")
def str_interactions(
    limit: int = Query(default=100, ge=1, le=1000),
    sponsor: Optional[str] = Query(default=None),  # noqa: UP045 (3.9 route sig)
    segment: Optional[str] = Query(default=None),  # noqa: UP045 (3.9 route sig)
) -> dict:
    """Return recent sponsor interactions (Hermes/Nemotron/Stripe), newest last, plus verify.

    Live and historical: the UI polls this; entries appended by acts appear on the next
    poll. Optional sponsor/segment filters power the per-segment interaction panels.
    """
    entries = read_interactions(
        limit=limit, sponsor=sponsor, segment=segment, path=_INTERACTIONS_PATH_STR
    )
    ok, message = verify_interactions(path=_INTERACTIONS_PATH_STR)
    return {
        "count": len(entries),
        "entries": entries,
        "verify": {"ok": ok, "message": message},
    }
