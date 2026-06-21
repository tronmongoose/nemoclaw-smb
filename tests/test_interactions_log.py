"""Tests for the hash-chained sponsor-interactions log."""
from __future__ import annotations

import json

import pytest

from agent.interactions_log import (
    append_interaction,
    read_interactions,
    verify_chain,
)


def test_append_and_read(tmp_path):
    p = str(tmp_path / "i.jsonl")
    append_interaction("NVIDIA", "anomaly reasoning", segment="owner", status="ok",
                       model="nvidia/nemotron", latency_ms=20.0, mode="live", path=p)
    append_interaction("Stripe", "MPP earn: price", segment="agent",
                       metadata={"amount_cents": 25}, path=p)
    entries = read_interactions(path=p)
    assert len(entries) == 2
    assert entries[0]["sponsor"] == "NVIDIA"
    assert entries[0]["segment"] == "owner"
    assert entries[1]["op"] == "MPP earn: price"
    assert entries[0]["seq"] == 0 and entries[1]["seq"] == 1


def test_verify_ok(tmp_path):
    p = str(tmp_path / "i.jsonl")
    append_interaction("NVIDIA", "a", path=p)
    append_interaction("Stripe", "b", path=p)
    ok, _msg = verify_chain(path=p)
    assert ok


def test_filters(tmp_path):
    p = str(tmp_path / "i.jsonl")
    append_interaction("NVIDIA", "a", segment="owner", path=p)
    append_interaction("Stripe", "b", segment="firm", path=p)
    assert len(read_interactions(sponsor="Stripe", path=p)) == 1
    assert len(read_interactions(segment="owner", path=p)) == 1


def test_unknown_sponsor_raises(tmp_path):
    with pytest.raises(ValueError):
        append_interaction("Bogus", "x", path=str(tmp_path / "i.jsonl"))


def test_tamper_detected(tmp_path):
    p = tmp_path / "i.jsonl"
    append_interaction("NVIDIA", "a", path=str(p))
    append_interaction("Stripe", "b", path=str(p))
    lines = p.read_text().splitlines()
    first = json.loads(lines[0])
    first["op"] = "TAMPERED"
    lines[0] = json.dumps(first)
    p.write_text("\n".join(lines) + "\n")
    ok, _msg = verify_chain(path=str(p))
    assert not ok
