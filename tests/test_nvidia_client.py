"""
test_nvidia_client.py — Unit tests for agent.nvidia_client (no live network calls).

Tests:
  - call_nemotron returns mock string when NVIDIA_NIM_API_KEY is unset.
  - nemotron_available() returns False when key is unset.
  - _strip_reasoning removes <think>...</think> blocks correctly.
"""

from __future__ import annotations

import pytest

from agent.nvidia_client import _MOCK_PREFIX, _strip_reasoning, call_nemotron, nemotron_available


def test_mock_when_key_absent(monkeypatch):
    """call_nemotron returns a '[nemotron-mock] ' prefixed string when key is unset."""
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    result = call_nemotron("test prompt")
    assert result.startswith(_MOCK_PREFIX)


def test_available_false_when_key_absent(monkeypatch):
    """nemotron_available() is False when NVIDIA_NIM_API_KEY is not in env."""
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    assert nemotron_available() is False


def test_available_true_when_key_present(monkeypatch):
    """nemotron_available() is True when NVIDIA_NIM_API_KEY is set."""
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "fake-key-for-test")
    assert nemotron_available() is True


def test_strip_reasoning_removes_think_block():
    """_strip_reasoning removes <think>...</think> and returns the remainder."""
    raw = "<think>blah blah internal reasoning</think>FINAL ANSWER"
    assert _strip_reasoning(raw) == "FINAL ANSWER"


def test_strip_reasoning_multiline_think():
    """_strip_reasoning handles multi-line <think> blocks."""
    raw = "<think>\nline1\nline2\n</think>\n\nReal answer here."
    assert _strip_reasoning(raw) == "Real answer here."


def test_strip_reasoning_no_think_block():
    """_strip_reasoning returns content unchanged when no <think> block present."""
    raw = "Plain answer with no thinking wrapper."
    assert _strip_reasoning(raw) == raw


def test_strip_reasoning_case_insensitive():
    """_strip_reasoning strips <THINK>...</THINK> regardless of case."""
    raw = "<THINK>ignore this</THINK>FINAL"
    assert _strip_reasoning(raw) == "FINAL"
