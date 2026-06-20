"""config -- STR agent configuration package.

STRUCTURE NOTE: act orchestrators live in acts/ (not agents/) to avoid colliding
with the existing agent/ package. Stripe primitives live in payments/ (not stripe/)
to avoid shadowing the stripe pip package.

Exports (re-exported for convenience):
    route_for       -- resolve task name to model identifier
    MODEL_ROUTING   -- full task-to-model mapping dict
    demo_mode       -- return True when DEMO_MODE env is enabled
    DEMO_MODE_ENV   -- name of the controlling environment variable
"""
from __future__ import annotations

from config.demo_mode import DEMO_MODE_ENV, demo_mode
from config.model_routing import MODEL_ROUTING, route_for

__all__ = ["route_for", "MODEL_ROUTING", "demo_mode", "DEMO_MODE_ENV"]
