"""demo: STR agent demo runner package.

STRUCTURE NOTE: Act orchestrators live in acts/ (not agents/) to avoid colliding
with the existing agent/ package. Stripe primitives live in payments/ (not stripe/)
to avoid shadowing the stripe pip package.

The full end-to-end demo runner (run_demo) ships in a later wave.
This module is importable now so later waves can drop in without restructuring.

Placeholder exports (not yet implemented):
    run_demo() -> None
"""
from __future__ import annotations
