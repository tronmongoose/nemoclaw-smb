"""loop.py — Weekly/monthly ingestion-and-analysis cycle runner for NemoClaw.

Exports: run_cycle

Cycle:
  1. Load connector state from data_root/state/connector.json.
  2. connector.fetch(tenant, state) -> new txns + updated state; persist state.
  3. Load full transaction set via ingestion.loader (deduped on disk).
  4. Update the KnowledgeGraph with new expense transactions.
  5. WEEKLY: anomaly+findings on newest period only; diff vs last findings;
     escalate only NEW findings to data_root/escalations.jsonl.
  6. MONTHLY: full compute_pnl + findings + build_report; diff+escalate new findings.
  7. Return a summary dict.

State files (all inside data_root/state/, never in the repo):
  connector.json — connector cursor / watermark (opaque per connector)
  findings.json  — last known findings set (used for diff to avoid re-escalation)

Escalation format (JSONL, one JSON object per line):
  {"ts": "<ISO>", "tenant": "<slug>", "mode": "weekly|monthly",
   "key": "<stable finding key>", "title": "<title>", "reason": "<why>"}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from connectors.base import ConnectorError, get_connector

if TYPE_CHECKING:
    from agent.tenancy import Tenant

_log = logging.getLogger(__name__)

_MODES = frozenset({"weekly", "monthly"})


# ---------------------------------------------------------------------------
# State persistence helpers
# ---------------------------------------------------------------------------

def _state_dir(tenant: "Tenant") -> Path:
    """Return and create data_root/state/ for state files."""
    path = Path(tenant.data_root) / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_connector_state(tenant: "Tenant") -> dict[str, Any]:
    """Read connector.json; return empty dict when absent or malformed."""
    path = _state_dir(tenant) / "connector.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning("loop: could not load connector state: %s", exc)
        return {}


def save_connector_state(tenant: "Tenant", state: dict[str, Any]) -> None:
    """Write connector.json atomically (write then rename)."""
    path = _state_dir(tenant) / "connector.json"
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        _log.warning("loop: could not save connector state: %s", exc)


def load_last_findings(tenant: "Tenant") -> dict[str, Any]:
    """Read findings.json; return empty dict when absent or malformed."""
    path = _state_dir(tenant) / "findings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning("loop: could not load last findings: %s", exc)
        return {}


def save_last_findings(tenant: "Tenant", findings_map: dict[str, Any]) -> None:
    """Write findings.json for next cycle's diff."""
    path = _state_dir(tenant) / "findings.json"
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(findings_map, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        _log.warning("loop: could not save findings state: %s", exc)


# ---------------------------------------------------------------------------
# Finding key + diff
# ---------------------------------------------------------------------------

def _finding_key(finding: Any) -> str:
    """Stable dedup key: title + category (survives cross-run restarts).

    monthly_impact and why contain numbers that drift; title+category is stable
    enough to detect whether the same underlying issue was previously seen.
    """
    return f"{finding.title}|{finding.category}"


def _diff_findings(
    current: list[Any],
    last_map: dict[str, Any],
) -> list[Any]:
    """Return findings whose key was NOT present in last_map.

    last_map keys are stable finding keys; their presence means the finding
    was already escalated in a prior cycle and must not re-fire.
    """
    return [f for f in current if _finding_key(f) not in last_map]


# ---------------------------------------------------------------------------
# Escalation writer
# ---------------------------------------------------------------------------

def _escalate(tenant: "Tenant", mode: str, new_findings: list[Any]) -> None:
    """Append one JSONL line per new finding to data_root/escalations.jsonl."""
    if not new_findings:
        return
    path = Path(tenant.data_root) / "escalations.jsonl"
    ts = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    try:
        with path.open("a", encoding="utf-8") as fh:
            for f in new_findings:
                record = {
                    "ts": ts,
                    "tenant": tenant.slug,
                    "mode": mode,
                    "key": _finding_key(f),
                    "title": f.title,
                    "reason": f.why,
                }
                fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        _log.warning("loop: could not write escalations: %s", exc)


# ---------------------------------------------------------------------------
# Graph population helper
# ---------------------------------------------------------------------------

def _populate_graph(graph: Any, transactions: list[dict[str, Any]]) -> None:
    """Load expense transactions into the KnowledgeGraph."""
    for tx in transactions:
        if tx.get("direction") == "expense":
            graph.record_payment(
                vendor=tx["vendor"],
                amount=tx["amount"],
                date=tx["date"],
                category=tx.get("category"),
            )


# ---------------------------------------------------------------------------
# Weekly cycle
# ---------------------------------------------------------------------------

def _newest_period_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return transactions from the most recent calendar month in the dataset."""
    if not transactions:
        return []
    latest_month = max(t.get("date", "")[:7] for t in transactions)
    return [t for t in transactions if t.get("date", "")[:7] == latest_month]


def _run_weekly(
    tenant: "Tenant",
    transactions: list[dict[str, Any]],
    graph: Any,
    last_findings_map: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    """Run anomaly scan on the newest period; return (new_findings, updated_map)."""
    from analysis.findings import find

    period_txns = _newest_period_transactions(transactions)
    findings = find(period_txns, graph, tenant.thresholds)
    new_findings = _diff_findings(findings, last_findings_map)
    updated_map = {_finding_key(f): {"title": f.title, "why": f.why} for f in findings}
    return new_findings, updated_map


# ---------------------------------------------------------------------------
# Monthly cycle
# ---------------------------------------------------------------------------

def _run_monthly(
    tenant: "Tenant",
    transactions: list[dict[str, Any]],
    graph: Any,
    last_findings_map: dict[str, Any],
) -> tuple[list[Any], dict[str, Any], str]:
    """Full P&L + findings + report; return (new_findings, updated_map, report_path)."""
    from analysis.pnl import compute_pnl
    from analysis.findings import find
    from analysis.report import build_report

    pnl = compute_pnl(transactions)
    findings = find(transactions, graph, tenant.thresholds)
    build_report(tenant, pnl, findings)

    new_findings = _diff_findings(findings, last_findings_map)
    updated_map = {_finding_key(f): {"title": f.title, "why": f.why} for f in findings}
    report_path = str(Path(tenant.data_root) / "report.md")
    return new_findings, updated_map, report_path


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_cycle(tenant: "Tenant", mode: str) -> dict[str, Any]:
    """Run one weekly or monthly ingestion+analysis cycle for a tenant.

    Returns a summary dict:
      connector: name of connector used
      txns_fetched: count from connector.fetch this run
      txns_total: total after loading full dataset from disk
      new_findings: count of findings not seen in the previous cycle
      report_path: report.md path (monthly only, else None)
      error: ConnectorError message if the connector failed (None on success)
    """
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got '{mode}'")

    connector = get_connector(tenant)
    connector_name = type(connector).__name__

    # Step 1: fetch new transactions via connector
    prior_state = load_connector_state(tenant)
    fetched_txns: list[dict[str, Any]] = []
    connector_error: str | None = None

    try:
        fetched_txns, new_state = connector.fetch(tenant, prior_state)
        save_connector_state(tenant, new_state)
        _log.info("loop: %s fetched %d txns for %s", connector_name, len(fetched_txns), tenant.slug)
    except ConnectorError as exc:
        connector_error = str(exc)
        _log.warning("loop: connector error for %s: %s", tenant.slug, exc)

    # Step 2: load full transaction set from disk (deduped by loader)
    from ingestion.loader import load_transactions
    from gbrain.knowledge_graph import KnowledgeGraph

    all_txns = load_transactions(tenant)
    graph = KnowledgeGraph()
    _populate_graph(graph, all_txns)

    last_findings_map = load_last_findings(tenant)

    report_path: str | None = None
    new_findings: list[Any] = []

    if mode == "weekly":
        new_findings, updated_map = _run_weekly(tenant, all_txns, graph, last_findings_map)
    else:
        new_findings, updated_map, report_path = _run_monthly(
            tenant, all_txns, graph, last_findings_map
        )

    _escalate(tenant, mode, new_findings)
    save_last_findings(tenant, updated_map)

    return {
        "connector": connector_name,
        "txns_fetched": len(fetched_txns),
        "txns_total": len(all_txns),
        "new_findings": len(new_findings),
        "report_path": report_path,
        "error": connector_error,
    }
