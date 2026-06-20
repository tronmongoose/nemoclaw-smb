"""tenant_analyze.py — Entry point for `make tenant-analyze TENANT=<slug>`.

Load tenant → load_transactions → build vendor/category graph → compute_pnl →
find advisory findings → build_report → print summary + report path.

Respects NEMOCLAW_TENANTS_ROOT env for real tenant directories outside the repo.
LLM calls are governed by route_llm(tenant) — restricted tenants stay local.
"""

from __future__ import annotations

import os
import sys


def _print_pnl_summary(pnl: dict) -> None:
    """Print P&L totals and per-month net to stdout."""
    totals = pnl.get("totals", {})
    print("\n=== P&L Summary ===")
    print(f"  Income:  ${totals.get('income', 0):>10,.2f}")
    print(f"  Expense: ${totals.get('expense', 0):>10,.2f}")
    print(f"  Net:     ${totals.get('net', 0):>10,.2f}")
    print()
    print("Monthly trend:")
    for entry in pnl.get("margin_trend", []):
        sign = "+" if entry["net"] >= 0 else ""
        print(f"  {entry['month']}  net {sign}${entry['net']:,.2f}")


def _print_findings(findings: list) -> None:
    """Print top advisory findings to stdout."""
    print("\n=== Top Advisory Findings ===")
    if not findings:
        print("  (none)")
        return
    for i, f in enumerate(findings[:5], 1):
        print(
            f"  {i}. [{f.confidence.upper()}] {f.title}\n"
            f"     Impact: ${f.monthly_impact:,.2f}/mo  ${f.annual_impact:,.2f}/yr\n"
            f"     {f.why}"
        )


def main() -> None:
    """Run the analysis pipeline for the named tenant."""
    slug = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("TENANT", "")
    )
    if not slug:
        print("Usage: python scripts/tenant_analyze.py <slug>", file=sys.stderr)
        sys.exit(1)

    from datetime import datetime, timezone

    from agent.tenancy import load_tenant
    from gbrain.knowledge_graph import KnowledgeGraph
    from ingestion import load_transactions
    from analysis import compute_pnl, find, build_report
    from analysis.export import write_analysis_json

    tenant = load_tenant(slug)
    print(f"Tenant: {tenant.slug}  |  sensitivity: {tenant.sensitivity}  |  routing: {tenant.llm_routing}")

    transactions = load_transactions(tenant)
    print(f"Loaded {len(transactions)} transactions from {tenant.data_root}")

    graph = KnowledgeGraph()
    for tx in transactions:
        if tx.get("direction") == "expense":
            graph.record_payment(
                vendor=tx["vendor"],
                amount=tx["amount"],
                date=tx["date"],
                category=tx.get("category"),
            )

    pnl = compute_pnl(transactions)
    findings = find(transactions, graph, tenant.thresholds)
    report = build_report(tenant, pnl, findings)

    generated_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    analysis_path = write_analysis_json(tenant, pnl, findings, generated_at)

    _print_pnl_summary(pnl)
    _print_findings(findings)

    from pathlib import Path
    report_path = Path(tenant.data_root) / "report.md"
    print(f"\nReport written to: {report_path}")
    print(f"Analysis JSON:    {analysis_path}")


if __name__ == "__main__":
    main()
