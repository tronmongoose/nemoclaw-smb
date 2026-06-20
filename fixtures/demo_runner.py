"""
demo_runner.py — End-to-end hackathon demo for NemoClaw SMB.

Runs a 6-scene arc (onboarding, anomaly, reasoning, execution, auto-pay, close)
against the seed data and prints a CEO-ready dashboard. Execute from repo root:
    python -m fixtures.demo_runner
"""

from __future__ import annotations

import os
import pathlib

# Configure state dir BEFORE importing handler modules so env vars take effect
# at module load time (audit_log reads NEMOCLAW_AUDIT_PATH at import).
_DEMO_STATE = pathlib.Path("./.demo_state")
_AUDIT_PATH = _DEMO_STATE / "audit.jsonl"
_APPROVALS_DIR = _DEMO_STATE / "approvals"
_DEMO_STATE.mkdir(exist_ok=True)
_APPROVALS_DIR.mkdir(exist_ok=True)
os.environ["NEMOCLAW_AUDIT_PATH"] = str(_AUDIT_PATH)
os.environ["NEMOCLAW_APPROVALS_DIR"] = str(_APPROVALS_DIR)

# Remove prior audit file so each demo run starts a fresh chain.
if _AUDIT_PATH.exists():
    _AUDIT_PATH.unlink()

from agent.audit_log import verify_chain  # noqa: E402
from agent import nemoclaw_harness  # noqa: E402
from agent.hermes_orchestrator import orchestrate  # noqa: E402
from fixtures.capture_run import load_capture  # noqa: E402
from fixtures.seed_data import (  # noqa: E402
    adobe_anomaly_402,
    affinity_alternative,
    aws_renewal_402,
    seed_invoices,
    studio_profile,
)
from gbrain.knowledge_graph import build_graph_from_invoices  # noqa: E402
from payments.payment_402_handler import handle_402  # noqa: E402
from payments.stripe_client import collect_fee  # noqa: E402
from agent.reasoning import analyze_vendors  # noqa: E402
from agent.skills.base import run_skill  # noqa: E402
from procurement.vendor_analyzer import build_analysis_prompt, rank_alternatives  # noqa: E402
from procurement.vendor_switcher import switch_vendor  # noqa: E402
import agent.skills.handle_402_skill       # noqa: F401,E402 — registers handle_402_skill
import agent.skills.access_governance_skill  # noqa: F401,E402 — registers access_governance_skill

_AUDIT_PATH_STR = str(_AUDIT_PATH)
_SEP = "-" * 60


def _header(title: str) -> None:
    """Print a section header with separator."""
    print(f"\n{_SEP}")
    print(title)
    print(_SEP)


def scene_hermes() -> None:
    """Replay a captured Hermes run or fall back to the live-mock orchestrate path."""
    _header("SCENE 0 -- Hermes Orchestrates the Loop")

    captured = load_capture()
    if captured is not None:
        print(f"[replay] intent: {captured['intent']}")
        result = captured
        tag = "[replay]"
    else:
        intent = "Check this month's invoices for overspend and handle the AWS renewal"
        print(f"[live-mock] Intent: {intent}")
        try:
            result = orchestrate(intent=intent, audit_path=_AUDIT_PATH_STR, max_steps=6)
        except Exception as exc:  # noqa: BLE001
            print(f"[Hermes] scene error (non-fatal): {exc}")
            return
        tag = "[live-mock]"

    for s in result["steps"]:
        h = s.get("audit_entry_hash") or ""
        print(f"{tag} [Hermes] step {s['step']}: {s['skill']} -> {s['outcome']} (audit {h[:8]})")
    if result["escalated"]:
        print(f"{tag} [Hermes] escalated — approval_request_id: {result['approval_request_id']}")
    print(f"{tag} [Hermes] final: {result['final']}")


def scene_1(graph) -> None:
    """Print studio profile and GBrain knowledge graph summary."""
    _header("SCENE 1 -- Onboarding")
    profile = studio_profile()
    print(f"Client: {profile['name']}  |  Headcount: {profile['headcount']}")
    ceo = next(c for c in profile["contacts"] if c["role"] == "CEO")
    print(f"CEO: {ceo['name']} <{ceo['email']}>")

    vendor_nodes = [n for n in graph.nodes() if n["type"] == "vendor"]
    all_edges = graph.edges()
    print(
        f"\nGBrain knowledge graph: {len(vendor_nodes)} vendor nodes,"
        f" {len(all_edges)} payment edges"
    )
    print("\nVendors loaded:")
    seen: set[str] = set()
    for node in vendor_nodes:
        label = node["label"]
        if label in seen:
            continue
        seen.add(label)
        history = graph.vendor_history(label)
        mo_avg = round(sum(history) / len(history), 2) if history else 0.0
        print(f"  {label:<28}  {node['category']:<20}  ${mo_avg:.2f}/mo avg")


def scene_2(graph) -> dict:
    """Run Adobe anomaly 402 and print escalation details. Returns outcome."""
    _header("SCENE 2 -- Anomaly Detection")
    event = adobe_anomaly_402()
    print(f"Incoming 402 event: {event['vendor']} ${event['amount']} on {event['date']}")

    result = handle_402(event, graph, audit_path=_AUDIT_PATH_STR)

    anomaly = result.get("anomaly") or {}
    reason = anomaly.get("reason", "n/a")
    print(f"\nAnomaly reason: {reason}")

    # Derive seat line from access_governance_skill (fixture-backed, offline-safe).
    _DEMO_REF_DATE = "2026-06-01"
    try:
        gov = run_skill("access_governance_skill", {"reference_date": _DEMO_REF_DATE})
        _adobe_unused = [
            s for s in gov["unused_seats"] if "adobe" in s["resource"].lower()
        ]
        _adobe_total = gov["seat_summary"].get("Adobe Creative Cloud", {}).get("total", 12)
        _unused_count = len(_adobe_unused)
        _seat_line = (
            f"ConductorOne/Baton: {_unused_count} of {_adobe_total} Adobe Creative Cloud"
            f" seats unused 60+ days -> deprovision candidates"
        )
    except Exception:  # noqa: BLE001
        _unused_count = 3
        _seat_line = "3 of your seats haven't been used in 60 days."

    print(f"\n{_seat_line}")

    ceo_msg = (
        "Adobe Creative Cloud renewal is $340, up from $277 last month. "
        "Outside your normal range. "
        f"{_unused_count} of your seats haven't been used in 60 days."
    )
    print(f"\nCEO message: {ceo_msg}")
    print(f"\nOutcome: {result['outcome']}")
    print(f"Approval request ID: {result['approval_request_id']}")
    return result


def scene_3() -> None:
    """Rank alternatives and show Nemotron prompt prefix."""
    _header("SCENE 3 -- Reasoning + Decision")
    current = {
        "vendor": "Adobe Creative Cloud",
        "amount": 340,
        "frequency": "monthly",
        "monthly_equivalent": 340,
    }
    alternatives = [
        affinity_alternative(),
        {"vendor": "Adobe Photography Plan", "amount": 120,
         "frequency": "monthly", "monthly_equivalent": 120},
    ]
    ranked = rank_alternatives(current, alternatives)
    print(f"Current: {current['vendor']} ${current['monthly_equivalent']:.2f}/mo\n")
    print("Ranked alternatives:")
    for alt in ranked:
        print(
            f"  [{alt['rank']}] {alt['vendor']:<30}"
            f"  ${alt['monthly_equivalent']:.2f}/mo"
            f"  saves ${alt['monthly_savings']:.2f}/mo"
            f"  (${alt['annual_savings']:.2f}/yr)"
        )

    _reasoning_ctx = {"client": "Pinwheel Studio", "seats_unused_60d": 3, "headcount": 12}
    if os.environ.get("NEMOCLAW_LIVE_REASONING") == "1":
        print("\nNemotron 3 Ultra live reasoning (may take 30-60s)...")
        analysis = analyze_vendors(current, ranked, context=_reasoning_ctx)
        print(analysis)
    else:
        print("\nNemotron 3 Ultra reasons over alternatives -- prompt preview (400 chars):")
        prompt = build_analysis_prompt(current, ranked, context=_reasoning_ctx)
        print(prompt[:400])


def scene_4(graph) -> dict:
    """Execute vendor switch from Adobe to Affinity. Returns switch result."""
    _header("SCENE 4 -- Execution")
    new_vendor = affinity_alternative()
    result = switch_vendor(
        "Adobe Creative Cloud", new_vendor, graph, audit_path=_AUDIT_PATH_STR
    )
    print(f"Switching '{result['old_vendor']}' -> '{new_vendor['vendor']}'")
    print("\nCascade steps:")
    for step in result["steps"]:
        print(f"  {step['step']:<24}  {step['status']:<10}  {step['detail']}")
    print(f"\nMonthly savings realized: ${result['monthly_savings']:.2f}")
    return result


def scene_5(graph) -> dict:
    """Auto-pay AWS renewal through NemoClaw harness. Returns outcome from inner 402 pipeline."""
    _header("SCENE 5 -- 402 in the Wild (Auto-Pay)")
    event = aws_renewal_402()
    aws_amount = float(event["amount"])
    print(f"Incoming 402 event: {event['vendor']} ${aws_amount} on {event['date']}")

    # threshold=500.0 matches payment_402_handler._DEFAULT_THRESHOLD so the
    # outer NemoClaw guard and the inner 402 handler use the same policy floor.
    harness_result = nemoclaw_harness.execute(
        "handle_402_skill",
        {"event": event, "invoices": seed_invoices()},
        amount=aws_amount,
        vendor="AWS",
        threshold=500.0,
        audit_path=_AUDIT_PATH_STR,
    )

    # Print NemoClaw pipeline steps
    step_names = " -> ".join(s["step"] + " " + s["status"] for s in harness_result["steps"])
    print(f"\n[NemoClaw] {step_names}")

    # The 402 pipeline result is nested inside harness_result["result"]
    inner = harness_result.get("result") or {}
    payment = inner.get("payment") or {}
    ledger = inner.get("ledger_entry") or {}
    print(f"\nOutcome: {inner.get('outcome', harness_result['outcome'])}")
    print(f"Stripe payment id: {payment.get('id', 'n/a')}")
    print(f"QuickBooks ledger entry: {ledger.get('entry_id', 'n/a')}")
    print("No CEO involvement.")
    # Prefer the inner 402 audit hash (the actual payment event); harness hash is the wrapper.
    audit_hash = inner.get("audit_entry_hash") or harness_result.get("audit_entry_hash")
    print(f"Audit entry hash: {audit_hash}")

    # Return a dict compatible with scene_6 (needs .amount and .audit_entry_hash at top level)
    return {
        "amount": aws_amount,
        "outcome": inner.get("outcome", harness_result["outcome"]),
        "audit_entry_hash": audit_hash,
        "payment": payment,
        "ledger_entry": ledger,
    }


def scene_6(aws_result: dict, switch_result: dict) -> None:
    """Print closing dashboard with savings, NemoClaw fee, and chain verification."""
    _header("SCENE 6 -- Close / Dashboard")

    # Savings: Adobe monthly elimination ($340/mo realized; $332.58/yr annualized vs Affinity)
    adobe_monthly = 340.00
    affinity_mo = affinity_alternative()["monthly_equivalent"]  # 7.42
    realized_monthly = round(adobe_monthly - affinity_mo, 2)
    annualized_projection = round(realized_monthly * 12, 2)

    print("Savings summary:")
    print(f"  Adobe -> Affinity (realized monthly):   ${realized_monthly:.2f}/mo")
    print(f"  Projected annualized (12 x monthly):    ${annualized_projection:.2f}/yr")
    print(f"  (Brief headline $1,847 includes multi-seat + seat-reclaim; labeled as projected)")

    invoices_auto_paid = 1  # AWS
    anomalies_handled = 1   # Adobe
    print(f"\nInvoices auto-paid this run: {invoices_auto_paid}  (AWS ${aws_result['amount']:.2f})")
    print(f"Anomalies escalated this run: {anomalies_handled}  (Adobe $340 spike)")

    # Fee: 0.5% of spend under management (amounts the agent touched this run)
    aws_amount = float(aws_result["amount"])
    adobe_amount = 340.00
    affinity_amount = affinity_alternative()["amount"]
    spend_under_management = aws_amount + adobe_amount + affinity_amount
    fee_amount = round(spend_under_management * 0.005, 2)
    fee_result = collect_fee(fee_amount, basis=f"demo_run_spend_${spend_under_management:.2f}")
    print(f"\nSpend under management: ${spend_under_management:.2f}")
    print(f"NemoClaw fee (0.5%): ${fee_amount:.2f}")
    print(f"  Stripe fee charge id: {fee_result['id']}")
    print(f"\nYou owe NemoClaw ${fee_amount:.2f}")

    ok, msg = verify_chain(_AUDIT_PATH_STR)
    print(f"\nAudit chain: {msg}  |  tamper-evident: {ok}")
    if _AUDIT_PATH.exists():
        import json as _json
        print("\nChain entries:")
        with _AUDIT_PATH.open("r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line:
                    continue
                _e = _json.loads(_line)
                _hash8 = str(_e.get("entry_hash", ""))[:8]
                print(
                    f"  [{_e.get('seq', '?'):>2}] {_e.get('action', ''):<20}"
                    f"  {_e.get('vendor', ''):<28}"
                    f"  ${float(_e.get('amount', 0)):>9.2f}"
                    f"  #{_hash8}"
                )


def main() -> None:
    """Run all 6 demo scenes in sequence."""
    print("NemoClaw SMB -- Hackathon Demo Run")
    print(f"Audit path: {_AUDIT_PATH_STR}")

    invoices = seed_invoices()
    graph = build_graph_from_invoices(invoices)

    scene_hermes()
    scene_1(graph)
    adobe_result = scene_2(graph)
    scene_3()
    scene_4(graph)
    aws_result = scene_5(graph)
    scene_6(aws_result, adobe_result)


if __name__ == "__main__":
    main()
