"""
test_capture.py — Offline tests for fixtures/capture_run.py and the demo replay path.

Tests:
  - capture(live=False) writes a file with all documented keys
  - load_capture round-trips the written file
  - load_capture returns None when the file is absent
  - scene_hermes replays without error when a capture file exists
"""

from __future__ import annotations

import json
import pathlib

import pytest


# ---------------------------------------------------------------------------
# capture — key presence and file output
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {"intent", "steps", "final", "escalated", "approval_request_id",
                  "audit_hashes", "captured_at"}


def test_capture_writes_file_with_required_keys(tmp_path: pathlib.Path):
    """capture(live=False) writes a JSON file containing all documented keys."""
    from fixtures.capture_run import capture

    out = str(tmp_path / "sub" / "run.json")
    result = capture(out_path=out, live=False)

    assert pathlib.Path(out).exists(), "capture did not create the output file"
    on_disk = json.loads(pathlib.Path(out).read_text(encoding="utf-8"))
    for key in _REQUIRED_KEYS:
        assert key in result, f"return dict missing key: {key}"
        assert key in on_disk, f"on-disk JSON missing key: {key}"


def test_capture_steps_is_list_of_dicts(tmp_path: pathlib.Path):
    """steps in the capture are a non-empty list with skill and outcome fields."""
    from fixtures.capture_run import capture

    out = str(tmp_path / "run.json")
    result = capture(out_path=out, live=False)

    assert isinstance(result["steps"], list)
    assert len(result["steps"]) > 0
    for step in result["steps"]:
        assert "skill" in step
        assert "outcome" in step


def test_capture_escalated_is_bool(tmp_path: pathlib.Path):
    """escalated field is a boolean (not None or string)."""
    from fixtures.capture_run import capture

    out = str(tmp_path / "run.json")
    result = capture(out_path=out, live=False)
    assert isinstance(result["escalated"], bool)


def test_capture_captured_at_injected_correctly(tmp_path: pathlib.Path):
    """captured_at is the value passed in, not a different timestamp."""
    from fixtures.capture_run import capture

    sentinel = "2099-01-01T00:00:00+00:00"
    out = str(tmp_path / "run.json")
    result = capture(out_path=out, live=False, captured_at=sentinel)
    assert result["captured_at"] == sentinel


# ---------------------------------------------------------------------------
# load_capture — round-trip and missing-file path
# ---------------------------------------------------------------------------

def test_load_capture_round_trips(tmp_path: pathlib.Path):
    """load_capture returns the same dict that capture wrote."""
    from fixtures.capture_run import capture, load_capture

    out = str(tmp_path / "run.json")
    written = capture(out_path=out, live=False)
    loaded = load_capture(out)
    assert loaded is not None
    assert loaded["intent"] == written["intent"]
    assert loaded["captured_at"] == written["captured_at"]


def test_load_capture_returns_none_when_absent(tmp_path: pathlib.Path):
    """load_capture returns None when the capture file does not exist."""
    from fixtures.capture_run import load_capture

    result = load_capture(str(tmp_path / "no_such_file.json"))
    assert result is None


# ---------------------------------------------------------------------------
# scene_hermes — replay branch
# ---------------------------------------------------------------------------

def test_scene_hermes_replays_without_error(tmp_path: pathlib.Path, monkeypatch, capsys):
    """scene_hermes prints [replay] lines and does not raise when a capture exists."""
    from fixtures.capture_run import capture
    import fixtures.capture_run as cr_module
    import fixtures.demo_runner as dr_module

    # Write a fresh capture to a temp path.
    out = str(tmp_path / "hermes_run.json")
    capture(out_path=out, live=False)

    # Patch load_capture in demo_runner to use the temp capture.
    monkeypatch.setattr(dr_module, "load_capture", lambda: cr_module.load_capture(out))

    # scene_hermes should not raise.
    dr_module.scene_hermes()

    captured_out = capsys.readouterr().out
    assert "[replay]" in captured_out
    assert "[Hermes]" in captured_out
