"""
baton_client.py — ConductorOne Baton access-governance integration for NemoClaw SMB.

Exports:
    AccessGrant       — dataclass: principal, resource, entitlement, last_used, source_connector
    baton_available   — True only when baton binary is on PATH
    fetch_access      — return list[AccessGrant] from real CLI or bundled fixture
    summarize_seats   — per-resource seat counts {app: {total, users:[...]}}
    unused_seats      — grants idle longer than `days` before reference_date
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "baton_access_sample.json"

#COMPLETION_DRIVE: baton CLI flag for JSON output is likely --output-format=json or -o json
#SUGGEST_VERIFY: run `baton access --help` against a real install to confirm the flag name
_BATON_JSON_FLAG = "--output-format=json"


@dataclass
class AccessGrant:
    """Single access grant linking a principal to an entitlement on a resource."""

    principal: str
    resource: str
    entitlement: str
    last_used: str | None
    source_connector: str


def baton_available() -> bool:
    """Return True only when the baton binary is on PATH."""
    return shutil.which("baton") is not None


def _parse_baton_output(raw: str) -> list[AccessGrant]:
    """Parse baton JSON output into AccessGrant list.

    #COMPLETION_DRIVE: baton's real JSON schema is unverified here; this helper
    is isolated so it can be corrected against real output without touching callers.
    #SUGGEST_VERIFY: run `baton access --output-format=json` against a live c1z
    and compare the top-level key and per-grant field names to what is parsed here.
    """
    data = json.loads(raw)
    items: list = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("grants", "access", "items", "results"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
    grants: list[AccessGrant] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        grants.append(AccessGrant(
            principal=str(item.get("principal", "")),
            resource=str(item.get("resource", "")),
            entitlement=str(item.get("entitlement", "")),
            last_used=item.get("last_used") or None,
            source_connector=str(item.get("source_connector", "baton")),
        ))
    return grants


def _load_fixture() -> list[AccessGrant]:
    """Load the bundled synthetic access fixture."""
    data = json.loads(_FIXTURE_PATH.read_text())
    items = data.get("grants", []) if isinstance(data, dict) else data
    grants: list[AccessGrant] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        grants.append(AccessGrant(
            principal=str(item.get("principal", "")),
            resource=str(item.get("resource", "")),
            entitlement=str(item.get("entitlement", "")),
            last_used=item.get("last_used") or None,
            source_connector=str(item.get("source_connector", "fixture")),
        ))
    return grants


def fetch_access(
    connector: str | None = None,
    c1z_path: str | None = None,
) -> tuple[list[AccessGrant], str]:
    """Return (grants, source) from the real baton CLI or the bundled fixture.

    source is "baton" when the CLI path is taken, "fixture" otherwise.
    Never raises to callers.
    """
    resolved_c1z = c1z_path or os.environ.get("BATON_C1Z")
    if baton_available() and resolved_c1z:
        try:
            cmd = ["baton", "access", _BATON_JSON_FLAG]
            if resolved_c1z:
                cmd += ["--c1z", resolved_c1z]
            if connector:
                cmd += ["--connector", connector]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                grants = _parse_baton_output(result.stdout)
                return grants, "baton"
        except Exception:  # noqa: BLE001
            pass
    return _load_fixture(), "fixture"


def summarize_seats(grants: list[AccessGrant]) -> dict:
    """Return per-resource seat counts: {resource: {total, users: [...]}}."""
    summary: dict[str, dict] = {}
    for g in grants:
        entry = summary.setdefault(g.resource, {"total": 0, "users": []})
        entry["total"] += 1
        if g.principal not in entry["users"]:
            entry["users"].append(g.principal)
    return summary


def unused_seats(
    grants: list[AccessGrant],
    days: int = 60,
    reference_date: str | None = None,
) -> list[AccessGrant]:
    """Return grants idle longer than `days` before reference_date.

    Grants with last_used=None are skipped (skip beats fabricate).
    reference_date defaults to today when not supplied; tests pass a fixed date.
    """
    ref = (
        datetime.fromisoformat(reference_date).date()
        if reference_date
        else date.today()
    )
    cutoff = ref - timedelta(days=days)
    result: list[AccessGrant] = []
    for g in grants:
        if g.last_used is None:
            continue
        try:
            used = datetime.fromisoformat(g.last_used).date()
        except ValueError:
            continue
        if used < cutoff:
            result.append(g)
    return result
