"""
capture_run.py — Capture or load a deterministic Hermes orchestration run.

Exports:
    capture      — run orchestrate() and serialize the result to JSON
    load_capture — deserialize a prior capture, or return None if absent
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import tempfile

_DEFAULT_INTENT = (
    "Review this month's invoices for overspend and decide whether to approve "
    "the AWS renewal."
)
_DEFAULT_OUT = "fixtures/captured/hermes_run.json"


def capture(
    intent: str | None = None,
    out_path: str = _DEFAULT_OUT,
    live: bool = False,
    captured_at: str | None = None,
) -> dict:
    """Run orchestrate() and write the full result dict to out_path as pretty JSON.

    When live=False (default) the mock llm is used — no network calls, deterministic.
    When live=True orchestrate uses call_hermes which requires NOUS_PORTAL_API_KEY.
    captured_at is written into the JSON; defaults to the current UTC timestamp when None.
    Returns the serialized dict.
    """
    # Deferred imports so module-level import never triggers network or env reads.
    from datetime import datetime, timezone  # noqa: PLC0415
    from agent.hermes_orchestrator import orchestrate  # noqa: PLC0415
    from agent.hermes_client import call_hermes, _scripted_mock  # noqa: PLC0415

    resolved_intent = intent or _DEFAULT_INTENT

    # Wire the llm: use a pure mock closure when live=False so there is zero
    # chance of a network attempt even if NOUS_PORTAL_API_KEY is accidentally set.
    #COMPLETION_DRIVE: live=True simply leaves llm as call_hermes (env-driven)
    if live:
        llm = call_hermes
    else:
        def llm(messages, *, system=None, **_):  # type: ignore[misc]
            """Offline mock: delegates to the scripted step sequence."""
            return _scripted_mock(messages)

    ts_now = captured_at or datetime.now(timezone.utc).isoformat()

    # Use a temp audit file so the capture does not pollute the demo audit chain.
    with tempfile.TemporaryDirectory() as tmp:
        audit_file = str(pathlib.Path(tmp) / "capture_audit.jsonl")
        approvals_dir = str(pathlib.Path(tmp) / "approvals")
        pathlib.Path(approvals_dir).mkdir()
        # Point harness to isolated tmp paths for this capture run.
        _prev_audit = os.environ.get("NEMOCLAW_AUDIT_PATH")
        _prev_approvals = os.environ.get("NEMOCLAW_APPROVALS_DIR")
        os.environ["NEMOCLAW_AUDIT_PATH"] = audit_file
        os.environ["NEMOCLAW_APPROVALS_DIR"] = approvals_dir
        try:
            result = orchestrate(intent=resolved_intent, llm=llm, audit_path=audit_file)
        finally:
            if _prev_audit is not None:
                os.environ["NEMOCLAW_AUDIT_PATH"] = _prev_audit
            else:
                os.environ.pop("NEMOCLAW_AUDIT_PATH", None)
            if _prev_approvals is not None:
                os.environ["NEMOCLAW_APPROVALS_DIR"] = _prev_approvals
            else:
                os.environ.pop("NEMOCLAW_APPROVALS_DIR", None)

    payload = {**result, "captured_at": ts_now}

    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def load_capture(path: str = _DEFAULT_OUT) -> dict | None:
    """Return a parsed capture dict from path, or None if the file is absent.

    Does not raise on missing file; raises json.JSONDecodeError on corrupt JSON.
    """
    p = pathlib.Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture a Hermes orchestration run.")
    parser.add_argument("--live", action="store_true", help="Use real Hermes API (requires NOUS_PORTAL_API_KEY)")
    parser.add_argument("--out", default=_DEFAULT_OUT, help="Output path")
    args = parser.parse_args()

    data = capture(out_path=args.out, live=args.live)
    steps = len(data.get("steps", []))
    escalated = data.get("escalated", False)
    final_preview = (data.get("final") or "")[:80]
    print(f"steps={steps} escalated={escalated} final={final_preview!r}")
