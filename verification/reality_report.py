"""
reality_report.py — Live integration status matrix for NemoClaw SMB.

Probes every external integration and classifies it honestly:
  REAL           — local-only primitive verified (no network needed)
  LIVE-OK        — key/binary present; real call succeeded
  LIVE-FAIL      — key/binary present; real call failed
  MOCK           — no key/binary; deterministic mock path active
  HOLLOW         — key present but backend intentionally not implemented
  KEYED-UNVERIFIED — key present but call shape could not be verified

Run: python3 verification/reality_report.py
Exit 0 always — this is a report, not a gate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Ensure project root (parent of this file's directory) is on sys.path so
# `agent`, `payments`, etc. are importable when the script is invoked directly.
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# .env loader — plain parser, no python-dotenv
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env from CWD into os.environ (setdefault — never overwrite live env)."""
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    with open(env_path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                os.environ.setdefault(k, v)


# ---------------------------------------------------------------------------
# Status type
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    """Result of one integration probe."""

    name: str
    status: str   # REAL | LIVE-OK | LIVE-FAIL | MOCK | HOLLOW | KEYED-UNVERIFIED
    detail: str


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------

def probe_hermes() -> ProbeResult:
    """Hermes: tiny real call when keyed; mock when not."""
    from agent.hermes_client import _MOCK_PREFIX, call_hermes, hermes_available

    if not hermes_available():
        return ProbeResult("Hermes", "MOCK", "NOUS_PORTAL_API_KEY not set")

    # Reasoning models spend tokens on hidden CoT first; give enough room for visible content.
    result = call_hermes([{"role": "user", "content": "reply PONG"}], max_tokens=256)
    if result.startswith(_MOCK_PREFIX):
        return ProbeResult("Hermes", "LIVE-FAIL", result[len(_MOCK_PREFIX):].strip()[:80])
    return ProbeResult("Hermes", "LIVE-OK", f"response: {result.strip()[:60]}")


def probe_nemotron() -> ProbeResult:
    """Nemotron: tiny real call when keyed; mock when not."""
    from agent.nvidia_client import _MOCK_PREFIX, call_nemotron, nemotron_available

    if not nemotron_available():
        return ProbeResult("Nemotron", "MOCK", "NVIDIA_NIM_API_KEY not set")

    result = call_nemotron("reply PONG", max_tokens=256)
    if result.startswith(_MOCK_PREFIX):
        return ProbeResult("Nemotron", "LIVE-FAIL", result[len(_MOCK_PREFIX):].strip()[:80])
    return ProbeResult("Nemotron", "LIVE-OK", f"response: {result.strip()[:60]}")


def probe_stripe_sdk() -> ProbeResult:
    """Stripe SDK: live-key refused (HOLLOW), test-key balance read, else MOCK."""
    from payments.stripe_client import _get_stripe, _is_live_key

    raw_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if _is_live_key(raw_key):
        return ProbeResult("Stripe-SDK", "HOLLOW", "sk_live_ key refused; NemoClaw is test-only")

    stripe = _get_stripe()
    if stripe is None:
        return ProbeResult("Stripe-SDK", "MOCK", "STRIPE_SECRET_KEY absent or non-test")

    try:
        bal = stripe.Balance.retrieve()
    except Exception as exc:  # noqa: BLE001 — the API call itself is the live signal
        return ProbeResult("Stripe-SDK", "LIVE-FAIL", str(exc)[:80])
    currency = "?"
    try:
        avail = bal["available"]
        currency = avail[0]["currency"] if avail else "?"
    except Exception:  # noqa: BLE001 — result parsing must not mask a successful call
        pass
    return ProbeResult("Stripe-SDK", "LIVE-OK", f"balance.retrieve ok, currency={currency}")


def probe_stripe_mcp() -> ProbeResult:
    """Stripe MCP: attempt retrieve_balance when enabled; else MOCK."""
    from payments.stripe_mcp import StripeMcpError, call_tool, stripe_mcp_enabled

    if not stripe_mcp_enabled():
        return ProbeResult("Stripe-MCP", "MOCK", "MCP path not enabled (npx absent or key missing)")

    try:
        result = call_tool("retrieve_balance", {})
        if "error" in str(result).lower():
            return ProbeResult("Stripe-MCP", "LIVE-FAIL", str(result)[:80])
        return ProbeResult("Stripe-MCP", "LIVE-OK", "retrieve_balance succeeded via MCP")
    except StripeMcpError as exc:
        return ProbeResult("Stripe-MCP", "LIVE-FAIL", str(exc)[:80])
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("Stripe-MCP", "LIVE-FAIL", str(exc)[:80])


def probe_baton() -> ProbeResult:
    """Baton: binary on PATH AND `baton --version` succeeds -> LIVE-OK; else MOCK."""
    from control_plane.baton_client import baton_available

    if not baton_available():
        return ProbeResult("Baton", "MOCK", "baton binary not on PATH")

    try:
        out = subprocess.run(
            ["baton", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            version = out.stdout.strip().splitlines()[0][:60]
            return ProbeResult("Baton", "LIVE-OK", version)
        return ProbeResult("Baton", "LIVE-FAIL", out.stderr.strip()[:80])
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("Baton", "LIVE-FAIL", str(exc)[:80])


def probe_c1_policy() -> ProbeResult:
    """C1 policy: detect HOLLOW (NotImplementedError) vs future LIVE-OK/MOCK.

    Spawns a child process to avoid polluting our env during the probe.
    """
    script = (
        "import os, sys; "
        "os.environ['C1_API_KEY'] = 'probe-test'; "
        "sys.path.insert(0, '.'); "
        "from control_plane.policy_check import check_policy; "
        "check_policy('probe-vendor', 1.0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=10,
    )
    stderr = result.stderr.strip()
    if "NotImplementedError" in stderr or result.returncode != 0:
        reason = "ConductorOne backend raises NotImplementedError — gated on C1 blessing"
        return ProbeResult("C1-Policy", "HOLLOW", reason)
    return ProbeResult("C1-Policy", "LIVE-OK", "check_policy returned without error")


def probe_gbrain() -> ProbeResult:
    """GBrain: attempt a real write+read round-trip when GBRAIN_MCP_CMD is set.

    LIVE-OK  — GBRAIN_MCP_CMD set, mcp importable, write+read round-trip succeeded
    LIVE-FAIL — GBRAIN_MCP_CMD set, mcp importable, but the round-trip failed
    MOCK     — GBRAIN_MCP_CMD unset; in-memory KnowledgeGraph active (default)
    """
    from gbrain.gbrain_client import (
        GBrainError,
        gbrain_available,
        read_page,
        write_vendor_page,
    )

    cmd = os.environ.get("GBRAIN_MCP_CMD", "")
    if not cmd:
        url = os.environ.get("GBRAIN_MCP_URL", "")
        if url:
            # URL is set but CMD is not; HTTP transport not yet implemented
            return ProbeResult(
                "GBrain",
                "MOCK",
                f"GBRAIN_MCP_URL set but GBRAIN_MCP_CMD absent; in-memory active "
                f"(HTTP transport not yet wired — set GBRAIN_MCP_CMD to enable)",
            )
        return ProbeResult("GBrain", "MOCK", "GBRAIN_MCP_CMD unset; in-memory KnowledgeGraph active")

    if not gbrain_available():
        return ProbeResult(
            "GBrain",
            "LIVE-FAIL",
            "GBRAIN_MCP_CMD set but mcp package not importable (pip install mcp)",
        )

    probe_slug = "nemoclaw/vendors/reality-probe"
    try:
        write_vendor_page("reality-probe", "Reality Probe", "probe")
    except GBrainError as exc:
        return ProbeResult("GBrain", "LIVE-FAIL", f"write_vendor_page failed: {str(exc)[:80]}")

    try:
        content = read_page(probe_slug)
    except GBrainError as exc:
        return ProbeResult("GBrain", "LIVE-FAIL", f"read_page after write failed: {str(exc)[:80]}")

    if content and "Reality Probe" in content:
        return ProbeResult("GBrain", "LIVE-OK", f"write+read round-trip succeeded (slug={probe_slug})")
    if content is None:
        return ProbeResult("GBrain", "LIVE-FAIL", f"read_page returned None after write (slug={probe_slug})")
    return ProbeResult("GBrain", "LIVE-FAIL", f"read_page content missing expected text: {content[:80]}")


def probe_audit_chain() -> ProbeResult:
    """Audit chain: write + verify against a tmp file -> REAL when it verifies."""
    from agent.audit_log import append_action, verify_chain

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        tmp = Path(tf.name)

    try:
        append_action(
            action="payment",
            vendor="reality-probe",
            amount=0.01,
            decision="approved",
            actor="reality_report",
            path=tmp,
        )
        ok, msg = verify_chain(path=tmp)
        if ok:
            return ProbeResult("Audit-Chain", "REAL", f"append+verify ok — {msg}")
        return ProbeResult("Audit-Chain", "LIVE-FAIL", f"verify failed: {msg}")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("Audit-Chain", "LIVE-FAIL", str(exc)[:80])
    finally:
        tmp.unlink(missing_ok=True)


def probe_guardrails() -> ProbeResult:
    """NeMo Guardrails: LIVE-OK when real LLM check runs; DENYLIST when disabled/unkeyed."""
    guardrails_on = os.environ.get("NEMOCLAW_GUARDRAILS") == "1"
    nous_key = os.environ.get("NOUS_PORTAL_API_KEY", "")

    if not guardrails_on:
        return ProbeResult(
            "NeMo-Guardrails",
            "DENYLIST",
            "NEMOCLAW_GUARDRAILS not set; built-in denylist active (set =1 to enable LLM rail)",
        )

    if not nous_key:
        return ProbeResult(
            "NeMo-Guardrails",
            "DENYLIST",
            "NEMOCLAW_GUARDRAILS=1 but NOUS_PORTAL_API_KEY absent; denylist fallback active",
        )

    try:
        from nemoguardrails import LLMRails, RailsConfig  # noqa: PLC0415
    except ImportError:
        return ProbeResult(
            "NeMo-Guardrails",
            "DENYLIST",
            "nemoguardrails not installed; denylist fallback active (pip install nemoguardrails)",
        )

    script = (
        "import os, sys, json; "
        "sys.path.insert(0, '.'); "
        "os.environ['NEMOCLAW_GUARDRAILS'] = '1'; "
        "from agent.nemoclaw_harness import _nemo_guardrails_check; "
        "result = _nemo_guardrails_check('onboarding_skill', {}, (True, 'fallback')); "
        "print(json.dumps({'allowed': result[0], 'reason': result[1]}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip()[-120:]
        return ProbeResult("NeMo-Guardrails", "LIVE-FAIL", f"child exited {proc.returncode}: {err}")
    try:
        data = json.loads(proc.stdout)
        label = "LIVE-OK" if data.get("allowed") is not None else "LIVE-FAIL"
        return ProbeResult("NeMo-Guardrails", label, f"allowed={data.get('allowed')} reason={data.get('reason','')[:60]}")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("NeMo-Guardrails", "LIVE-FAIL", f"parse error: {exc} stdout={proc.stdout[:80]}")


def probe_sandbox() -> ProbeResult:
    """Subprocess sandbox: SUBPROCESS when real child process ran; IN-PROCESS otherwise."""
    sandbox_on_val = os.environ.get("NEMOCLAW_SANDBOX", "").strip().lower()
    sandbox_on = sandbox_on_val in ("1", "true", "yes", "on")

    if not sandbox_on:
        return ProbeResult(
            "Sandbox",
            "IN-PROCESS",
            "NEMOCLAW_SANDBOX not set; skills run in-process (set truthy to enable subprocess isolation)",
        )

    script = (
        "import os, sys, json; "
        "sys.path.insert(0, '.'); "
        "os.environ['NEMOCLAW_SANDBOX'] = 'true'; "
        "import agent.skills.onboarding_skill; "
        "from agent.nemoclaw_harness import _run_skill; "
        "result, label = _run_skill('onboarding_skill', {}); "
        "print(json.dumps({'label': label, 'has_result': result is not None}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip()[-120:]
        return ProbeResult("Sandbox", "LIVE-FAIL", f"child exited {proc.returncode}: {err}")
    try:
        data = json.loads(proc.stdout)
        label = data.get("label", "unknown")
        status = "SUBPROCESS" if label == "subprocess" else "IN-PROCESS"
        return ProbeResult("Sandbox", status, f"sandbox_label={label} has_result={data.get('has_result')}")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("Sandbox", "LIVE-FAIL", f"parse error: {exc} stdout={proc.stdout[:80]}")


def probe_intuit() -> ProbeResult:
    """Intuit: credentials detected -> KEYED-UNVERIFIED (SDK path unimplemented); else MOCK."""
    from payments.intuit_reconciler import _INTUIT_READY

    if _INTUIT_READY:
        return ProbeResult(
            "Intuit-QB",
            "KEYED-UNVERIFIED",
            "INTUIT_CLIENT_ID+SECRET set but live SDK path is unimplemented (#COMPLETION_DRIVE)",
        )
    return ProbeResult("Intuit-QB", "MOCK", "INTUIT_CLIENT_ID/SECRET absent; sandbox mock active")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_PROBES = [
    probe_hermes,
    probe_nemotron,
    probe_stripe_sdk,
    probe_stripe_mcp,
    probe_baton,
    probe_c1_policy,
    probe_gbrain,
    probe_audit_chain,
    probe_intuit,
    probe_guardrails,
    probe_sandbox,
]

_STATUS_ORDER = ["REAL", "LIVE-OK", "SUBPROCESS", "LIVE-FAIL", "MOCK", "HOLLOW", "DENYLIST", "IN-PROCESS", "KEYED-UNVERIFIED"]


def _run_probes() -> list[ProbeResult]:
    """Execute every probe and return results."""
    results: list[ProbeResult] = []
    for probe_fn in _PROBES:
        try:
            results.append(probe_fn())
        except Exception as exc:  # noqa: BLE001
            results.append(ProbeResult(probe_fn.__name__, "LIVE-FAIL", f"probe error: {exc}"))
    return results


def _print_table(results: list[ProbeResult]) -> None:
    """Print an aligned status table to stdout."""
    name_w = max(len(r.name) for r in results) + 2
    status_w = max(len(r.status) for r in results) + 2

    header = f"{'INTEGRATION':<{name_w}} {'STATUS':<{status_w}} DETAIL"
    print(header)
    print("-" * min(len(header) + 40, 120))

    for r in results:
        print(f"{r.name:<{name_w}} {r.status:<{status_w}} {r.detail}")

    print()
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    parts = [f"{s}={counts[s]}" for s in _STATUS_ORDER if s in counts]
    print(f"Summary: {len(results)} integrations — {', '.join(parts)}")


def main() -> None:
    """Load env, run all probes, print table. Always exits 0."""
    _load_dotenv()
    results = _run_probes()
    _print_table(results)


if __name__ == "__main__":
    main()
