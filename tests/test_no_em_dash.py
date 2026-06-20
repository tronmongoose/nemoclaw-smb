"""tests/test_no_em_dash.py -- Guard against em-dash characters in STR agent source.

Scans acts/, skills/, payments/envelopes.py, data/, config/, demo/, and
control_plane/c1_governance.py for the Unicode em-dash character (U+2014).
Fails on first file that contains one so the output is immediately actionable.
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_EM_DASH = "—"

_SCAN_TARGETS: list[Path] = [
    _REPO_ROOT / "acts",
    _REPO_ROOT / "skills",
    _REPO_ROOT / "payments" / "envelopes.py",
    _REPO_ROOT / "data",
    _REPO_ROOT / "config",
    _REPO_ROOT / "demo",
    _REPO_ROOT / "control_plane" / "c1_governance.py",
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


def test_no_em_dash_in_str_agent_sources() -> None:
    """Fail when any STR agent source file contains an em-dash character."""
    py_files = _collect_py_files(_SCAN_TARGETS)
    assert py_files, "No .py files found to scan -- check _SCAN_TARGETS"

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
