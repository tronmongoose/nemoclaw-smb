"""config/demo_mode.py -- First-class DEMO_MODE flag for the STR agent.

When DEMO_MODE is true, Stripe primitives log-but-mock instead of executing
real payment calls. Default is true so no keys are needed to run the demo.

Public API:
    DEMO_MODE_ENV   -- name of the controlling environment variable ("DEMO_MODE")
    demo_mode()     -- return True when demo mode is active
"""
from __future__ import annotations

import os

DEMO_MODE_ENV: str = "DEMO_MODE"

_TRUTHY = frozenset(("1", "true", "yes", "on"))


def demo_mode() -> bool:
    """Return True when DEMO_MODE env var is set to a truthy value, or when unset.

    Default is True so the demo runs without any credentials configured.
    """
    raw = os.environ.get(DEMO_MODE_ENV, "true").strip().lower()
    return raw in _TRUTHY
