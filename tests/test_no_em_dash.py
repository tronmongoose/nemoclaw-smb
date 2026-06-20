"""tests/test_no_em_dash.py: Guard against em-dash characters in STR agent source.

Scans acts/, skills/, payments/envelopes.py, data/, config/, demo/,
control_plane/c1_governance.py, the remaining STR payments files, README.md,
and docs/submission.md for:
  1. The Unicode em-dash character (U+2014).
  2. Prose use of ` -- ` (space double-hyphen space) as an em-dash aside.

Fenced code blocks (```...```) and backtick spans (`...`) in README/submission
prose are excluded from the ` -- ` check so legitimate CLI flag examples like
`--api-key` or `--live` do not false-positive.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_EM_DASH = "—"

# Regex that matches prose ` -- ` (space, two hyphens, space).
# Flags: no MULTILINE needed; we test line by line.
_PROSE_DOUBLE_HYPHEN = re.compile(r" -- ")

# Regex matching a word character immediately before or after `--`,
# which means it is a CLI flag (e.g. `--api-key`, `--live`) rather than an aside.
# Used to skip false-positives on lines that contain only CLI-style `--word`.
_CLI_FLAG_PAT = re.compile(r"--\w")

_PY_SCAN_TARGETS: list[Path] = [
    _REPO_ROOT / "acts",
    _REPO_ROOT / "skills",
    _REPO_ROOT / "payments" / "envelopes.py",
    _REPO_ROOT / "payments" / "issuing.py",
    _REPO_ROOT / "payments" / "payouts.py",
    _REPO_ROOT / "payments" / "connect.py",
    _REPO_ROOT / "payments" / "metronome.py",
    _REPO_ROOT / "payments" / "mpp_server.py",
    _REPO_ROOT / "data",
    _REPO_ROOT / "config",
    _REPO_ROOT / "demo",
    _REPO_ROOT / "control_plane" / "c1_governance.py",
]

_PROSE_SCAN_TARGETS: list[Path] = [
    _REPO_ROOT / "README.md",
    _REPO_ROOT / "docs" / "submission.md",
]


def _collect_py_files(targets: list[Path]) -> list[Path]:
    """Return all .py files under the given paths (files or directories)."""
    files: list[Path] = []
    for target in targets:
        if target.is_file() and target.suffix == ".py":
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.rglob("*.py")))
    return files


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced code blocks (``` ... ```) from markdown text.

    Returns the text with fenced block content replaced by blank lines so line
    numbers remain stable for error reporting.
    """
    result: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            result.append("\n")  # keep line count stable
            continue
        if in_fence:
            result.append("\n")
        else:
            result.append(line)
    return "".join(result)


def _strip_backtick_spans(line: str) -> str:
    """Remove inline backtick spans from a line of text."""
    return re.sub(r"`[^`]*`", "", line)


def test_no_em_dash_in_str_agent_sources() -> None:
    """Fail when any STR agent source .py file contains an em-dash character."""
    py_files = _collect_py_files(_PY_SCAN_TARGETS)
    assert py_files, "No .py files found to scan: check _PY_SCAN_TARGETS"

    violations: list[str] = []
    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _EM_DASH in text:
            lines = [
                f"  line {i+1}: {line.rstrip()}"
                for i, line in enumerate(text.splitlines())
                if _EM_DASH in line
            ]
            violations.append(f"{path.relative_to(_REPO_ROOT)}:\n" + "\n".join(lines))

    assert not violations, (
        f"Em-dash (U+2014) found in {len(violations)} file(s):\n"
        + "\n".join(violations)
    )


def test_no_prose_double_hyphen_in_str_agent_sources() -> None:
    """Fail when any STR agent .py source uses ' -- ' as an em-dash aside."""
    py_files = _collect_py_files(_PY_SCAN_TARGETS)
    assert py_files, "No .py files found to scan: check _PY_SCAN_TARGETS"

    violations: list[str] = []
    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines()):
            if _PROSE_DOUBLE_HYPHEN.search(line):
                violations.append(
                    f"  {path.relative_to(_REPO_ROOT)} line {i+1}: {line.rstrip()}"
                )

    assert not violations, (
        f"Prose ' -- ' aside found in {len(violations)} location(s):\n"
        + "\n".join(violations)
    )


def test_no_em_dash_or_prose_double_hyphen_in_docs() -> None:
    """Fail when README.md or docs/submission.md contains em-dash or prose ' -- '.

    Fenced code blocks and backtick spans are excluded from the ' -- ' check
    so CLI flag examples like ``--api-key`` do not false-positive.
    """
    violations: list[str] = []

    for path in _PROSE_SCAN_TARGETS:
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Check em-dash in the full raw text.
        if _EM_DASH in raw:
            for i, line in enumerate(raw.splitlines()):
                if _EM_DASH in line:
                    violations.append(
                        f"  {path.relative_to(_REPO_ROOT)} line {i+1} [em-dash]: {line.rstrip()}"
                    )

        # Check prose ' -- ' after stripping fences and backtick spans.
        prose_text = _strip_fenced_blocks(raw)
        for i, line in enumerate(prose_text.splitlines()):
            scrubbed = _strip_backtick_spans(line)
            if _PROSE_DOUBLE_HYPHEN.search(scrubbed):
                violations.append(
                    f"  {path.relative_to(_REPO_ROOT)} line {i+1} [prose --]: {line.rstrip()}"
                )

    assert not violations, (
        f"Em-dash or prose ' -- ' found in docs:\n" + "\n".join(violations)
    )
