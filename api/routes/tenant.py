"""tenant.py — Local operator endpoint: GET /tenant/{slug}/analysis.

Local/operator endpoint only. No auth, no multi-tenant public exposure.
Reads analysis.json produced by write_analysis_json from a local file; never
calls an LLM or external service. Finance figures stay on-machine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from agent.tenancy import ConfigError, load_tenant

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/{slug}/analysis")
def get_tenant_analysis(slug: str) -> dict[str, Any]:
    """Return the latest analysis.json for a tenant; 404 when not yet generated."""
    try:
        tenant = load_tenant(slug)
    except ConfigError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    analysis_path = Path(tenant.data_root) / "analysis.json"
    if not analysis_path.exists():
        raise HTTPException(
            status_code=404,
            detail="analysis.json not found — run tenant-analyze first",
        )

    try:
        return json.loads(analysis_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not read analysis.json: {exc}") from exc
