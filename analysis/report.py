"""report.py — Markdown report builder for per-tenant analysis output.

Exports: build_report

Generates a complete Markdown report from P&L data and advisory findings.
Optionally appends a one-paragraph narrative summary via route_llm(tenant)
(local for restricted tenants). LLM call is wrapped in try/except; the report
is fully usable without it — LLM failure degrades gracefully to no narrative.

Report is written to tenant.data_root/report.md and the markdown string returned.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.tenancy import Tenant
    from analysis.findings import Finding

_log = logging.getLogger(__name__)

_PNL_TABLE_HEADER = "| Month | Income | Expense | Net |"
_PNL_TABLE_SEP    = "|-------|--------|---------|-----|"


def _pnl_table(pnl: dict[str, Any]) -> str:
    """Render monthly P&L as a markdown table."""
    lines = [_PNL_TABLE_HEADER, _PNL_TABLE_SEP]
    for month, data in pnl.get("monthly", {}).items():
        lines.append(
            f"| {month} | ${data['income']:,.2f} | ${data['expense']:,.2f} | ${data['net']:,.2f} |"
        )
    totals = pnl.get("totals", {})
    lines.append(
        f"| **Total** | **${totals.get('income', 0):,.2f}** | "
        f"**${totals.get('expense', 0):,.2f}** | **${totals.get('net', 0):,.2f}** |"
    )
    return "\n".join(lines)


def _category_table(pnl: dict[str, Any]) -> str:
    """Render expense by category as a markdown table (aggregated across all months)."""
    cat_totals: dict[str, float] = {}
    for data in pnl.get("monthly", {}).values():
        for cat, amt in data.get("by_category", {}).items():
            cat_totals[cat] = cat_totals.get(cat, 0.0) + amt

    if not cat_totals:
        return "_No category data._"

    lines = ["| Category | Total |", "|----------|-------|"]
    for cat, total in sorted(cat_totals.items(), key=lambda x: -abs(x[1])):
        lines.append(f"| {cat} | ${total:,.2f} |")
    return "\n".join(lines)


def _findings_section(findings: list["Finding"]) -> str:
    """Render ranked findings as a markdown section."""
    if not findings:
        return "_No advisory findings._"

    lines: list[str] = []
    for i, f in enumerate(findings, 1):
        lines.append(
            f"**{i}. {f.title}** ({f.confidence} confidence)\n"
            f"- Category: {f.category}\n"
            f"- Monthly impact: ${f.monthly_impact:,.2f} | Annual: ${f.annual_impact:,.2f}\n"
            f"- {f.why}"
        )
    return "\n\n".join(lines)


def _try_narrative(
    tenant: "Tenant",
    pnl: dict[str, Any],
    findings: list["Finding"],
) -> str | None:
    """Generate a one-paragraph narrative via route_llm(tenant); return None on any failure.

    This is the ONLY LLM call in the pipeline. For restricted tenants, route_llm
    returns call_local (Ollama), so finance data never reaches a frontier API.
    """
    try:
        from agent.claw_router import route_llm

        llm = route_llm(tenant)
        totals = pnl.get("totals", {})
        top_findings = findings[:3]
        finding_lines = "\n".join(
            f"- {f.title}: {f.why}" for f in top_findings
        )
        prompt = (
            f"Summarize this SMB financial snapshot in one paragraph (3-5 sentences). "
            f"Income: ${totals.get('income', 0):,.2f}, "
            f"Expense: ${totals.get('expense', 0):,.2f}, "
            f"Net: ${totals.get('net', 0):,.2f}. "
            f"Top findings:\n{finding_lines}\n"
            f"Use only the numbers above. Be direct and quantitative."
        )
        response = llm([{"role": "user", "content": prompt}], max_tokens=200)
        if response and not response.startswith("[local-mock]"):
            return response.strip()
        return None
    except Exception as exc:  # noqa: BLE001
        _log.debug("report: narrative LLM call skipped: %s", exc)
        return None


def build_report(
    tenant: "Tenant",
    pnl: dict[str, Any],
    findings: list["Finding"],
) -> str:
    """Build and write a Markdown report for the tenant analysis.

    Writes to tenant.data_root/report.md.
    Returns the markdown string (complete without LLM narrative).
    """
    totals = pnl.get("totals", {})
    months = list(pnl.get("monthly", {}).keys())
    date_range = f"{min(months)} to {max(months)}" if months else "N/A"

    sections: list[str] = [
        f"# Financial Analysis Report: {tenant.slug}",
        f"Period: {date_range}  |  Sensitivity: {tenant.sensitivity}  |  Mode: {tenant.mode}",
        "",
        "## Monthly P&L",
        _pnl_table(pnl),
        "",
        "## Expense by Category",
        _category_table(pnl),
        "",
        "## Advisory Findings",
        _findings_section(findings),
    ]

    narrative = _try_narrative(tenant, pnl, findings)
    if narrative:
        sections.extend(["", "## Executive Summary", narrative])

    report = "\n".join(sections) + "\n"

    report_path = Path(tenant.data_root) / "report.md"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
    except OSError as exc:
        _log.warning("report: could not write report.md: %s", exc)

    return report
