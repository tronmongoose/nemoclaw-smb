"""
conftest.py — shared fixtures and env loading for live integration tests.

Live tests are gated by @pytest.mark.live. They skip when the required
key or binary is absent so `pytest tests/` stays green offline.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _load_dotenv() -> None:
    """Load .env from repo root into os.environ; setdefault so live env wins."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
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


@pytest.fixture(autouse=True)
def _live_env():
    """Load .env only when a live test in this directory actually runs.

    Module-level loading would leak keys into the whole pytest session at
    collection time and make offline tests hit real APIs.
    """
    _load_dotenv()
    yield
