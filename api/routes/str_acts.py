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

from acts.platform_agent import (
    get_metrics,
    serve_aeo_call,
    serve_guest_comms_call,
    serve_pricing_call,
)
from acts.property_mgmt_agent import (
    analyze_performance,
    calculate_ubp_invoices,
    clean_stalls,
    detect_stalls,
    get_portfolio_summary,
    get_turnover,
    handle_checkout_event,
    run_month_end_payouts,
)
from acts.str_owner_agent import reconcile_month
from agent.audit_log import verify_chain
from agent.interactions_log import append_interaction, read_interactions
from agent.interactions_log import verify_chain as verify_interactions
from api.seed import DEMO_AUDIT_PATH, DEMO_INTERACTIONS_PATH
from payments.issuing import issue_cleaner_card
from payments.mpp_server import (
    AEO_AUDIT_ENDPOINT_CENTS,
    GUEST_COMMS_ENDPOINT_CENTS,
    _extract_token,
    validate_mpp_token,
)
from skills.cleaner_scheduling_skill import draft_cleaner_schedule
from skills.coordination_skill import draft_coordination_nudge
from skills.performance_analysis_skill import summarize_performance

router = APIRouter(prefix="/str", tags=["str-acts"])

# Earn events and act payments write to the shared demo audit chain so /str/audit
# can read them back and verify integrity end to end.
_AUDIT_PATH_STR: str = str(DEMO_AUDIT_PATH)

# audit "actor" / token-id substrings that mark an entry as STR-scoped.
_STR_ACTORS = frozenset({"str-owner-agent", "cleaner-subagent", "property-mgmt-agent"})
_STR_SERVICES = frozenset({"price", "aeo-audit", "guest-comms"})

# Live-result cache: a live call is slow (real Nemotron / Hermes inference), so the first
# call per input is computed live and cached, and reloads serve the cached real result
# instantly, still labeled LIVE with the true model + latency. `fresh=true` forces a new
# call (the on-camera "watch it run live" moment). Demo-mode calls are already fast and
# are not cached.
# GLOBAL-STATE: process-local demo cache so filmed loads are instant
_LIVE_CACHE: dict[str, dict] = {}


def _cached_live(key: str, fresh: bool):
    """Return a cached live result for key, or None when absent or fresh is forced."""
    if fresh:
        return None
    return _LIVE_CACHE.get(key)


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


class GuestCommsBody(BaseModel):
    """Request body for POST /str/act3/guest-comms."""

    guest_context: str
    property_id: str
    inquiry_type: str = "general"


class NudgeBody(BaseModel):
    """Request body for POST /str/stalls/nudge."""

    handoff_id: str


# ---------------------------------------------------------------------------
# Act I: owner-fee reconciliation
# ---------------------------------------------------------------------------


@router.get("/act1/{property_id}/{month}")
def act1_reconcile(
    property_id: str,
    month: str,
    live: bool = Query(default=False),
    fresh: bool = Query(default=False),
) -> dict:
    """Run Act I reconciliation; serialize the full report incl. provenance.

    The `anomaly` block carries reasoning_provenance (mode, model, latency_ms,
    source). `live` is threaded through to detect_fee_anomaly's reasoning path.
    Live results are cached so reloads are instant; `fresh=true` forces a new call.
    """
    key = f"act1:{property_id}:{month}"
    if live:
        cached = _cached_live(key, fresh)
        if cached is not None:
            return cached
    report = reconcile_month(property_id, month, live=live)
    result = asdict(report)
    if live:
        _LIVE_CACHE[key] = result
    return result


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
    fresh: bool = Query(default=False),
    authorization: Optional[str] = Header(default=None),  # noqa: UP045 (3.9 route sig)
) -> dict:
    """Serve a pricing call through Act III and log the earn event.

    An optional Authorization bearer token selects the demo token; absent or
    malformed headers fall back to the platform default. `live` threads to the
    pricing reasoning so a real Nemotron call fires when a key is present.
    Live results are cached so reloads are instant; `fresh=true` forces a new call.
    """
    token = _extract_token(authorization) or "mpp_tok_demo"
    key = f"price:{body.property_id}:{body.season}:{body.day_of_week}"
    if live:
        cached = _cached_live(key, fresh)
        if cached is not None:
            return cached
    result = serve_pricing_call(
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
    if live:
        _LIVE_CACHE[key] = result
    return result


@router.post("/act3/aeo-audit")
def act3_aeo_audit(
    body: AEOBody,
    live: bool = Query(default=False),
    fresh: bool = Query(default=False),
    authorization: Optional[str] = Header(default=None),  # noqa: UP045 (3.9 route sig)
):
    """The real 402-then-200 earn loop: no token -> 402, mpp_tok_ token -> 200.

    Returns a JSONResponse with status 402 (and the Stripe-MPP WWW-Authenticate
    header) when no valid token is present, else serves the AEO audit and logs
    the earn event. `live` threads to the AEO reasoning so a real Nemotron call
    fires when a key is present. Live results are cached; `fresh=true` forces a new call.
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
    key = f"aeo:{hash(body.listing_text)}"
    if live:
        cached = _cached_live(key, fresh)
        if cached is not None:
            return cached
    result = serve_aeo_call(
        listing_text=body.listing_text,
        amenities_list=body.amenities_list,
        existing_schema=body.existing_schema,
        listing_url=body.listing_url,
        demo_token=token,
        audit_path=_AUDIT_PATH_STR,
        live=live,
    )
    if live:
        _LIVE_CACHE[key] = result
    return result


@router.post("/act3/guest-comms")
def act3_guest_comms(
    body: GuestCommsBody,
    live: bool = Query(default=False),
    fresh: bool = Query(default=False),
    authorization: Optional[str] = Header(default=None),  # noqa: UP045 (3.9 route sig)
):
    """402-then-200 earn loop for guest comms (Sales): no token -> 402, mpp_tok_ -> 200.

    Calls Nous Hermes to triage guest inquiry intent and draft a reply with one upsell.
    live threads to draft_guest_comms so a real Hermes call fires when a key is present.
    Live results are cached; `fresh=true` forces a new call.
    """
    token = _extract_token(authorization)
    if not token or not validate_mpp_token(token):
        amount_dollars = GUEST_COMMS_ENDPOINT_CENTS / 100
        return JSONResponse(
            status_code=402,
            content={"error": "payment_required", "amount_cents": GUEST_COMMS_ENDPOINT_CENTS},
            headers={
                "WWW-Authenticate": f"stripe-mpp charge=${amount_dollars:.2f} currency=usd"
            },
        )
    key = f"guest-comms:{hash(body.guest_context)}:{body.inquiry_type}"
    if live:
        cached = _cached_live(key, fresh)
        if cached is not None:
            return cached
    result = serve_guest_comms_call(
        guest_context=body.guest_context,
        property_id=body.property_id,
        inquiry_type=body.inquiry_type,
        demo_token=token,
        audit_path=_AUDIT_PATH_STR,
        live=live,
    )
    if live:
        _LIVE_CACHE[key] = result
    return result


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


# ---------------------------------------------------------------------------
# Turnover coordination: the loop, the stall queue, and the Hermes nudge
# ---------------------------------------------------------------------------

# Handoff ids whose coordination interaction has already been logged this process,
# so polling /str/stalls surfaces the coordination agent once without flooding the feed.
# GLOBAL-STATE: process-local dedupe for the demo interactions feed
_NUDGE_LOGGED: set = set()


def _log_coordination(handoff: dict, prov: dict) -> None:
    """Append one Nous-Hermes coordination interaction for the agent-at-work feed."""
    append_interaction(
        sponsor="Nous Research",
        op=f"turnover: nudge drafted ({handoff['from_actor']} -> {handoff['to_actor']})",
        segment="firm",
        status="ok",
        model=prov.get("model"),
        latency_ms=prov.get("latency_ms"),
        mode=prov.get("mode"),
        metadata={"handoff_id": handoff["handoff_id"], "property_id": handoff["property_id"]},
        path=_INTERACTIONS_PATH_STR,
    )


@router.get("/turnover")
def str_turnover(
    property_id: Optional[str] = Query(default=None),  # noqa: UP045 (3.9 route sig)
    live: bool = Query(default=False),  # noqa: ARG001 (uniform live param; state is deterministic)
) -> dict:
    """Return turnover-loop state (checkout -> clean -> inspect -> ready) per property."""
    events = get_turnover(property_id)
    return {"properties": [asdict(e) for e in events]}


@router.get("/stalls")
def str_stalls(live: bool = Query(default=False)) -> dict:
    """Return blocked handoffs, each with a Hermes-drafted nudge + reasoning provenance.

    `live` threads to draft_coordination_nudge so a real Hermes call fires per stall
    when a Nous key is present; otherwise a deterministic demo nudge is returned. The
    coordination interaction is logged once per handoff so the agent floor sees it.
    """
    stalls = detect_stalls()
    out: list = []
    for h in stalls:
        nudge = draft_coordination_nudge(h, live=live)
        prov = nudge["reasoning_provenance"]
        if h["handoff_id"] not in _NUDGE_LOGGED:
            _log_coordination(h, prov)
            _NUDGE_LOGGED.add(h["handoff_id"])
        out.append({**h, "nudge": nudge, "reasoning_provenance": prov})
    return {"count": len(out), "stalls": out}


@router.post("/stalls/nudge")
def str_stalls_nudge(body: NudgeBody, live: bool = Query(default=False)) -> dict:
    """Re-draft the nudge for one stalled handoff and log the coordination action.

    Demo-safe: drafts and logs the nudge for the agent floor; no external message
    is sent. Returns the handoff plus the freshly drafted nudge.
    """
    match = next((h for h in detect_stalls() if h["handoff_id"] == body.handoff_id), None)
    if match is None:
        return {"ok": False, "reason": f"unknown handoff {body.handoff_id!r}"}
    nudge = draft_coordination_nudge(match, live=live)
    prov = nudge["reasoning_provenance"]
    _log_coordination(match, prov)
    return {"ok": True, **match, "nudge": nudge, "reasoning_provenance": prov}


# ---------------------------------------------------------------------------
# Performance flagging + cleaner scheduling (Hermes connective tissue)
# ---------------------------------------------------------------------------

# GLOBAL-STATE: process-local dedupe so polling surfaces each agent once, not per poll.
_PERF_LOGGED: set = set()
_SCHED_LOGGED: set = set()


def _log_firm_hermes(op: str, prov: dict, metadata: dict) -> None:
    """Append one Nous-Hermes firm interaction for the agent-at-work feed."""
    append_interaction(
        sponsor="Nous Research",
        op=op,
        segment="firm",
        status="ok",
        model=prov.get("model"),
        latency_ms=prov.get("latency_ms"),
        mode=prov.get("mode"),
        metadata=metadata,
        path=_INTERACTIONS_PATH_STR,
    )


@router.get("/performance")
def str_performance(live: bool = Query(default=False)) -> dict:
    """Rank properties vs the portfolio average with a Hermes-written 'why' per property."""
    out: list = []
    for perf in analyze_performance():
        analysis = summarize_performance(perf, live=live)
        prov = analysis["reasoning_provenance"]
        if perf["property_id"] not in _PERF_LOGGED:
            _log_firm_hermes(
                f"performance: {perf['property_name']} {perf['status']}",
                prov, {"property_id": perf["property_id"]},
            )
            _PERF_LOGGED.add(perf["property_id"])
        out.append({**perf, "analysis": analysis, "reasoning_provenance": prov})
    return {"count": len(out), "properties": out}


@router.get("/scheduling")
def str_scheduling(live: bool = Query(default=False)) -> dict:
    """Clean-stage stalls with crew availability + a Hermes reassign/schedule draft."""
    out: list = []
    for cs in clean_stalls():
        schedule = draft_cleaner_schedule(cs, live=live)
        prov = schedule["reasoning_provenance"]
        if cs["handoff_id"] not in _SCHED_LOGGED:
            _log_firm_hermes(
                f"scheduling: reassign {cs['property_name']}",
                prov, {"handoff_id": cs["handoff_id"]},
            )
            _SCHED_LOGGED.add(cs["handoff_id"])
        out.append({**cs, "schedule": schedule, "reasoning_provenance": prov})
    return {"count": len(out), "stalls": out}


@router.post("/scheduling/assign")
def str_scheduling_assign(body: NudgeBody, live: bool = Query(default=False)) -> dict:
    """Reassign a stalled cleaning to the free cleaner and pre-authorize their card.

    Drafts the schedule, then issues a single-use cleaner card (demo-mocked) to the
    suggested free cleaner. This is the 'pay + schedule' tie. No external send.
    """
    match = next((cs for cs in clean_stalls() if cs["handoff_id"] == body.handoff_id), None)
    if match is None:
        return {"ok": False, "reason": f"unknown handoff {body.handoff_id!r}"}
    suggested = match.get("suggested_cleaner")
    if not suggested:
        return {"ok": False, "reason": "no free cleaner available to reassign"}

    schedule = draft_cleaner_schedule(match, live=live)
    _log_firm_hermes(
        f"scheduling: reassign {match['property_name']}",
        schedule["reasoning_provenance"], {"handoff_id": match["handoff_id"]},
    )
    card = issue_cleaner_card(
        job_id=f"job-{match['property_id']}-reassign",
        property_id=match["property_id"],
        cleaner_id=suggested["id"],
    )
    append_interaction(
        sponsor="Stripe", op="scheduling: cleaner card pre-authorized", segment="firm",
        status="ok", metadata={"handoff_id": match["handoff_id"], "cleaner": suggested["name"]},
        path=_INTERACTIONS_PATH_STR,
    )
    return {
        "ok": True,
        "handoff_id": match["handoff_id"],
        "cleaner": suggested["name"],
        "card_token": card.card_token,
        "schedule": schedule,
    }
