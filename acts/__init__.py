"""acts -- STR agent act orchestrators.

STRUCTURE NOTE: Act orchestrators live here (not in agents/) to avoid colliding
with the existing agent/ package. Stripe primitives live in payments/ (not stripe/)
to avoid shadowing the stripe pip package.

Three acts ship in later waves:
    acts.str_owner_agent    -- Act I: STR Owner Agent (anomaly detection, fee reconciliation)
    acts.property_mgmt_agent -- Act II: Property Management Agent (crew dispatch, AEO)
    acts.platform_agent     -- Act III: Platform Agent (dynamic pricing, NHI governance)

This init exposes stub imports so `from acts import str_owner_agent` works once
the wave modules land.
"""
from __future__ import annotations
