"""
hermes_client.py — Thin Nous Research Hermes client (OpenAI-compatible endpoint).

Exports: call_hermes, hermes_available, _MOCK_PREFIX, _HERMES_DEFAULT_BASE_URL.

Mirrors the nvidia_client.py seam pattern: httpx, timeout, try/except, fail-soft
to a deterministic scripted mock when the key is absent or any error occurs.
The mock drives a coherent multi-step plan so the orchestrator iterates offline.
"""

from __future__ import annotations

import json
import os

import httpx

_HERMES_DEFAULT_BASE_URL: str = "https://inference-api.nousresearch.com/v1"
# Verified against Nous docs (hermes-agent.nousresearch.com/docs/integrations/providers):
# OpenAI-compatible /v1/chat/completions. Portal prefers scoped inference:invoke JWTs;
# NOUS_PORTAL_API_KEY (static key from Portal API settings) is the bearer fallback path.

_MOCK_PREFIX = "[hermes-mock] "

# Scripted offline steps keyed by step index (0-based count of tool/observation turns).
# Each step is a JSON action string so the orchestrator can parse it normally.
# #COMPLETION_DRIVE: scripted-for-demo — uses real skill names + seed_data-valid args
_MOCK_STEPS: list[str] = [
    json.dumps({
        "action": "run_skill",
        "skill": "anomaly_detect_skill",
        "args": {"invoices": "__SEED__", "z_threshold": 2.0},
        "reason": "Check invoices for spend anomalies as first diagnostic step.",
    }),
    json.dumps({
        "action": "run_skill",
        "skill": "invoice_ingest_skill",
        "args": {"invoices": "__SEED__"},
        "reason": "Ingest invoices into graph records for recurring-subscription view.",
    }),
    json.dumps({
        "action": "final",
        "summary": (
            "Anomaly scan complete. Adobe Creative Cloud shows a +23% spike ($340 vs ~$277 avg). "
            "Invoice graph loaded 4 recurring vendors. Recommend human review of Adobe renewal "
            "before auto-pay. AWS renewal is within normal range."
        ),
    }),
]


def hermes_available() -> bool:
    """Return True when NOUS_PORTAL_API_KEY is set and non-empty in the environment."""
    return bool(os.environ.get("NOUS_PORTAL_API_KEY"))


def call_hermes(
    messages: list[dict],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    system: str | None = None,
) -> str:
    """POST messages to the Nous Portal Hermes chat/completions endpoint.

    Returns the assistant content string.
    Falls back to a deterministic scripted-mock string (prefixed '[hermes-mock] ')
    when NOUS_PORTAL_API_KEY is unset or any network/API error occurs. Never raises.
    The mock inspects the number of prior tool/observation turns in messages to
    return the Nth scripted JSON action so the orchestrator iterates offline.
    """
    if not hermes_available():
        return _scripted_mock(messages)

    api_key = os.environ["NOUS_PORTAL_API_KEY"]
    base_url = os.environ.get("NOUS_PORTAL_BASE_URL", _HERMES_DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("HERMES_MODEL", "hermes-agent")

    full_messages: list[dict] = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    payload = {
        "model": model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content: str = data["choices"][0]["message"].get("content") or ""
        return content if content else f"{_MOCK_PREFIX}empty response"

    except Exception as exc:  # noqa: BLE001
        return f"{_MOCK_PREFIX}error: {exc}"


def _scripted_mock(messages: list[dict]) -> str:
    """Return the Nth scripted JSON action based on prior observation turn count.

    Counts turns whose role is 'tool' or content contains 'observation:' to
    determine which step index to return. Caps at the last scripted step.
    """
    obs_count = sum(
        1 for m in messages
        if m.get("role") == "tool"
        or (isinstance(m.get("content"), str) and m["content"].startswith("observation:"))
    )
    idx = min(obs_count, len(_MOCK_STEPS) - 1)
    return _MOCK_PREFIX + _MOCK_STEPS[idx]
