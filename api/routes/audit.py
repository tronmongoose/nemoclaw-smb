"""Audit log read route for nemoclaw-smb dashboard.

Exports (via router):
    GET /audit  — read demo audit chain entries + verify integrity
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from agent.audit_log import verify_chain
from api.seed import DEMO_AUDIT_PATH

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def get_audit(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    """Return audit chain entries (newest last) and hash-chain verification.

    Response shape:
        {
          count:   int,
          entries: [ ...raw audit entry dicts... ],
          verify:  {ok: bool, message: str}
        }

    If the demo audit file does not exist, returns count=0, entries=[], verify.ok=True.
    """
    if not DEMO_AUDIT_PATH.exists():
        return {"count": 0, "entries": [], "verify": {"ok": True, "message": "empty"}}

    entries: list[dict] = []
    with DEMO_AUDIT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    # Return newest-last (natural append order); truncate to limit from the tail.
    entries = entries[-limit:]

    ok, message = verify_chain(path=str(DEMO_AUDIT_PATH))
    return {
        "count": len(entries),
        "entries": entries,
        "verify": {"ok": ok, "message": message},
    }
