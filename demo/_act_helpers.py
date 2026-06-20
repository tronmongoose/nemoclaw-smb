"""demo/_act_helpers.py -- Display helpers for the three-act STR demo runner.

Provides formatted console output for ledger tables, card issuance results,
payout batches, AEO breakdowns, and MPP 402/200 exchanges. All output targets
a 1080p screen recording with clear separators and aligned columns.

Public API:
    print_act_header(title)
    pause_for_narration(msg)
    show_ledger_table(summary)
    show_anomaly_catch(anomaly)
    show_nhi(nhi_id, scopes, label)
    show_approval_hold(amount_cents)
    show_payment_result(payment)
    show_card_result(card)
    show_payout_batch(batch)
    show_ubp_invoice(invoice)
    show_mpp_exchange(status, body, label)
    show_aeo_breakdown(aeo_result)
    show_metrics(metrics)
    show_audit_tail(ok, detail)
"""
from __future__ import annotations

import json
from typing import Any

# Colorama is optional; fall back to plain text when absent.
try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=True)
    _GREEN = Fore.GREEN
    _YELLOW = Fore.YELLOW
    _RED = Fore.RED
    _CYAN = Fore.CYAN
    _BOLD = Style.BRIGHT
    _RESET = Style.RESET_ALL
except ImportError:
    _GREEN = _YELLOW = _RED = _CYAN = _BOLD = _RESET = ""

_SEP_FULL = "=" * 72
_SEP_THIN = "-" * 72


def _c(color: str, text: str) -> str:
    """Wrap text in color code if colorama is available."""
    return f"{color}{text}{_RESET}"


def print_act_header(title: str) -> None:
    """Print a bold act header with full-width separator."""
    print(f"\n{_SEP_FULL}")
    print(_c(_BOLD + _CYAN, f"  {title}"))
    print(_SEP_FULL)


def pause_for_narration(msg: str) -> None:
    """Print a narration cue. No I/O pause in automated runs."""
    print(f"\n{_c(_YELLOW, '>>>')} {msg}")


def show_ledger_table(summary: Any) -> None:
    """Print an aligned financial column table for the ledger summary."""
    rev = summary.revenue_cents / 100
    contract_pct = summary.contract_pct * 100
    charged_pct = summary.charged_pct * 100
    contract_fee = summary.line_items["contracted_fee_cents"] / 100
    charged_fee = summary.line_items["charged_fee_cents"] / 100
    delta = summary.line_items["fee_delta_cents"] / 100

    print(f"\n  Property  : {summary.property_id}   Month: {summary.month}")
    print(_SEP_THIN)
    print(f"  {'Item':<30} {'Amount':>10}")
    print(_SEP_THIN)
    print(f"  {'Monthly revenue':<30} {'${:>8.2f}'.format(rev):>10}")
    print(f"  {'Contract rate':<30} {'{:>8.1f}%'.format(contract_pct):>10}")
    print(f"  {'Charged rate':<30} {'{:>8.1f}%'.format(charged_pct):>10}")
    print(f"  {'Expected management fee':<30} {'${:>8.2f}'.format(contract_fee):>10}")
    print(f"  {'Charged management fee':<30} {'${:>8.2f}'.format(charged_fee):>10}")
    delta_str = "${:>8.2f}".format(abs(delta))
    direction = "OVERCHARGE" if delta > 0 else ("UNDERCHARGE" if delta < 0 else "MATCH")
    color = _RED if delta != 0 else _GREEN
    print(f"  {'Delta':<30} {_c(color, f'{delta_str} {direction}'):>10}")
    print(_SEP_THIN)


def show_anomaly_catch(anomaly: Any) -> None:
    """Print the anomaly detection result with reasoning trace."""
    flag = _c(_RED, "ANOMALY DETECTED") if anomaly.is_anomaly else _c(_GREEN, "NO ANOMALY")
    print(f"\n  Anomaly check : {flag}")
    print(f"  Reason        : {anomaly.reason}")
    print(f"  Model used    : {anomaly.model_used}")
    print(f"\n  Reasoning trace:")
    for line in anomaly.reasoning_trace.split(". "):
        if line.strip():
            print(f"    {line.rstrip('.')}.")


def show_nhi(nhi_id: str, scopes: list[str], label: str = "Agent NHI") -> None:
    """Print a ConductorOne NHI record."""
    print(f"\n  {_c(_BOLD, label)}")
    print(f"    ID     : {_c(_CYAN, nhi_id)}")
    print(f"    Scopes : {', '.join(scopes)}")
    print(f"    Source : conductorone-synthetic-demo")


def show_approval_hold(amount_cents: int) -> None:
    """Print the REQUIRE_APPROVAL gate message."""
    print(f"\n  {_c(_YELLOW, 'REQUIRE_APPROVAL')} -- corrected fee ${amount_cents / 100:.2f}")
    print("  Payment held for human approval before any funds move.")


def show_payment_result(payment: Any) -> None:
    """Print a signed payment result with Carryall envelope fields."""
    print(f"\n  {_c(_GREEN, 'Payment approved and executed')}")
    print(f"    Payment ID   : {payment.payment_id}")
    print(f"    Amount       : ${payment.amount_cents / 100:.2f}")
    print(f"    Status       : {payment.status}")
    print(f"    Audit hash   : {payment.audit_hash[:20]}...")
    print(f"    Envelope     : Ed25519-signed Carryall envelope (ephemeral demo key)")


def show_card_result(card: Any) -> None:
    """Print a cleaner card issuance result. Never shows PAN."""
    print(f"\n  {_c(_GREEN, 'Single-use card issued')}")
    print(f"    Token (no PAN)   : {card.card_token}")
    print(f"    Card ID          : {card.card_id}")
    print(f"    Amount cap       : ${card.amount_cap_cents / 100:.2f}")
    print(f"    MCC restrictions : {', '.join(card.mcc_list)}")
    print(f"    Expiry           : {card.expiry_utc[:10]} EOD UTC")
    print(f"    Backend          : {card.backend}")


def show_payout_batch(batch: Any) -> None:
    """Print the month-end payout batch in an aligned table."""
    print(f"\n  {_c(_BOLD, 'Month-end Global Payouts')}  ({batch.month})")
    print(_SEP_THIN)
    print(f"  {'Crew':<25} {'Role':<15} {'Amount':>10}  {'Transfer ID'}")
    print(_SEP_THIN)
    for r in batch.records:
        print(
            f"  {r.crew_name:<25} {r.status:<15} "
            f"{'${:>8.2f}'.format(r.amount_cents / 100):>10}  {r.transfer_id}"
        )
    print(_SEP_THIN)
    print(f"  {'TOTAL':<40} {'${:>8.2f}'.format(batch.total_cents / 100):>10}")


def show_ubp_invoice(invoice: Any) -> None:
    """Print a UBP owner invoice."""
    print(f"\n  {_c(_BOLD, 'UBP Invoice')}  owner={invoice.owner_id}  id={invoice.invoice_id}")
    print(_SEP_THIN)
    for line in invoice.line_items:
        print(f"  {line.property_name:<30} {line.description}")
        print(f"  {'':30} Fee: ${line.fee_cents / 100:.2f}")
    print(_SEP_THIN)
    print(f"  Total platform fee: ${invoice.total_fee_cents / 100:.2f}")


def show_mpp_exchange(status: int, body: dict, label: str) -> None:
    """Print one side of the MPP 402/200 exchange."""
    color = _RED if status == 402 else _GREEN
    print(f"\n  {_c(color, f'HTTP {status}')}  [{label}]")
    for k, v in body.items():
        print(f"    {k:<20}: {v}")


def show_aeo_breakdown(aeo_result: Any) -> None:
    """Print the AEO score breakdown, CRITICAL flag, and optimized opening."""
    ds = aeo_result.dimension_scores
    print(f"\n  {_c(_BOLD, 'AEO Audit -- Sweet Clementine by the Sea')}")
    print(f"  Overall score : {_c(_RED if aeo_result.overall_score < 70 else _GREEN, str(aeo_result.overall_score))}/100")
    print(_SEP_THIN)
    print(f"  {'Dimension':<35} {'Score':>6} / 25")
    print(_SEP_THIN)
    print(f"  {'Structure completeness':<35} {ds.structure_completeness:>6}")
    print(f"  {'Agent parseability':<35} {ds.agent_parseability:>6}")
    print(f"  {'Description quality':<35} {ds.description_quality:>6}")
    print(f"  {'Conflict-free':<35} {ds.conflict_free:>6}")
    print(_SEP_THIN)

    critical_flags = [f for f in aeo_result.critical_flags if f.severity == "CRITICAL"]
    if critical_flags:
        flag = critical_flags[0]
        print(f"\n  {_c(_RED, 'CRITICAL:')} {flag.code}")
        print(f"  {flag.plain_english}")

    print(f"\n  {_c(_BOLD, 'Optimized opening paragraph:')}")
    print(f"  {aeo_result.optimized_opening}")

    print(f"\n  {_c(_BOLD, 'JSON-LD schema snippet:')}")
    snippet = {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "checkinTime": aeo_result.json_ld_schema.get("checkinTime"),
        "checkoutTime": aeo_result.json_ld_schema.get("checkoutTime"),
        "petsAllowed": aeo_result.json_ld_schema.get("petsAllowed"),
        "x-str-pet-policy": aeo_result.json_ld_schema.get("x-str-pet-policy"),
    }
    print(json.dumps(snippet, indent=4))


def show_metrics(metrics: dict) -> None:
    """Print platform earn metrics."""
    print(f"\n  {_c(_BOLD, 'Platform Earn Metrics')}")
    print(f"    Calls served         : {metrics['calls_served']}")
    print(f"    Revenue earned       : ${metrics['revenue_earned_dollars']:.2f}")
    print(f"    Properties optimized : {metrics['properties_optimized']}")


def show_audit_tail(ok: bool, detail: str) -> None:
    """Print the audit chain verification result."""
    color = _GREEN if ok else _RED
    status = "VALID" if ok else "TAMPERED"
    print(f"\n  Audit chain: {_c(color, status)}  ({detail})")
