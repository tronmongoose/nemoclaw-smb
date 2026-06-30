"""
nvidia_client.py — Thin NVIDIA NIM client for Nemotron 3 Ultra.

Exports: call_nemotron, nemotron_available, _strip_reasoning, DEFAULT_MODEL.
"""

from __future__ import annotations

import os
import re

import httpx

DEFAULT_MODEL: str = os.environ.get(
    "NEMOTRON_MODEL", "nvidia/nemotron-ultra-253b-v1"
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_MOCK_PREFIX = "[nemotron-mock] "


def nemotron_available() -> bool:
    """Return True when NVIDIA_NIM_API_KEY is set in the environment."""
    return bool(os.environ.get("NVIDIA_NIM_API_KEY"))


def _strip_reasoning(text: str) -> str:
    """Remove <think>...</think> blocks and return the remainder, stripped.

    Pure helper — no I/O, no env reads.
    """
    stripped = _THINK_RE.sub("", text)
    return stripped.strip()


def call_nemotron(
    prompt: str,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    system: str | None = None,
) -> str:
    """POST prompt to the NVIDIA NIM /chat/completions endpoint.

    Returns the final answer text with chain-of-thought stripped.
    Falls back to a deterministic mock string (prefixed '[nemotron-mock] ')
    when NVIDIA_NIM_API_KEY is unset or any network/API error occurs.
    Never raises to callers.

    #COMPLETION_DRIVE: NVIDIA_NIM_BASE_URL defaults to the public NIM endpoint.
    """
    if not nemotron_available():
        return f"{_MOCK_PREFIX}NVIDIA_NIM_API_KEY not set"

    api_key = os.environ["NVIDIA_NIM_API_KEY"]
    base_url = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.environ.get("NEMOTRON_MODEL", DEFAULT_MODEL)

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
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

        choice = data["choices"][0]["message"]
        content: str = choice.get("content") or ""
        return _strip_reasoning(content) if content else f"{_MOCK_PREFIX}empty response"

    except Exception as exc:  # noqa: BLE001
        return f"{_MOCK_PREFIX}error: {exc}"
