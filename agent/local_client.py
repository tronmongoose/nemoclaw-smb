"""
local_client.py — Local Ollama LLM provider for NemoClaw.

Exports: call_local, local_available, _MOCK_PREFIX, _LOCAL_DEFAULT_BASE_URL, _LOCAL_DEFAULT_MODEL.

Mirrors the hermes_client / nvidia_client seam: httpx, timeout, try/except,
fail-soft to a deterministic mock string when Ollama is unreachable or returns
an error. Never raises to callers.

#COMPLETION_DRIVE: Ollama OpenAI-compatible endpoint is /v1/chat/completions
(confirmed against Ollama v0.1.x+ docs — the /api/chat endpoint is Ollama-native;
/v1/chat/completions is the OpenAI-compat shim enabled by default).
Default model "gemma2:27b" — matches bjornswarm's primary local model.
#SUGGEST_VERIFY: run `ollama list` to confirm the exact model tag on this machine.
"""

from __future__ import annotations

import os

import httpx

_LOCAL_DEFAULT_BASE_URL: str = "http://localhost:11434/v1"
_LOCAL_DEFAULT_MODEL: str = "gemma2:27b"
_MOCK_PREFIX = "[local-mock] "


def local_available() -> bool:
    """Return True when the Ollama /v1/models endpoint is reachable.

    Fast probe — uses a short timeout so tests and offline runs don't block.
    """
    base = os.environ.get("OLLAMA_BASE_URL", _LOCAL_DEFAULT_BASE_URL).rstrip("/")
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{base}/models")
            return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def call_local(
    messages: list[dict],
    model: str | None = None,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    system: str | None = None,
) -> str:
    """POST messages to the Ollama OpenAI-compatible /v1/chat/completions endpoint.

    Returns the assistant content string.
    Falls back to a mock string (prefixed '[local-mock] ') on any error or when
    Ollama is unreachable. Never raises.

    model defaults to OLLAMA_MODEL env or _LOCAL_DEFAULT_MODEL ("gemma2:27b").
    base URL defaults to OLLAMA_BASE_URL or "http://localhost:11434/v1".
    """
    resolved_model = model or os.environ.get("OLLAMA_MODEL", _LOCAL_DEFAULT_MODEL)
    base = os.environ.get("OLLAMA_BASE_URL", _LOCAL_DEFAULT_BASE_URL).rstrip("/")

    full_messages: list[dict] = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    payload = {
        "model": resolved_model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{base}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        content: str = data["choices"][0]["message"].get("content") or ""
        return content if content else f"{_MOCK_PREFIX}empty response from {resolved_model}"

    except Exception as exc:  # noqa: BLE001
        return f"{_MOCK_PREFIX}error: {exc}"
