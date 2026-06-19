"""tenant_run.py — Entry point for `make tenant-run TENANT=<slug>`.

Loads the named tenant, resolves its config, and prints the resolved config
plus the LLM routing decision. The ingestion/P&L pipeline is a later build;
this file wires the entry point only.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Load tenant from argv[1] (or TENANT env) and print resolved config."""
    import os
    slug = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TENANT", "")
    if not slug:
        print("Usage: python scripts/tenant_run.py <slug>", file=sys.stderr)
        sys.exit(1)

    from agent.tenancy import load_tenant
    from agent.claw_router import route_llm

    t = load_tenant(slug)
    fn = route_llm(t)

    print(f"slug:         {t.slug}")
    print(f"sensitivity:  {t.sensitivity}")
    print(f"mode:         {t.mode}")
    print(f"llm_routing:  {t.llm_routing}")
    print(f"data_root:    {t.data_root}")
    print(f"brain_path:   {t.brain_path}")
    print(f"audit_path:   {t.audit_path}")
    print(f"thresholds:   {t.thresholds}")
    print(f"llm_callable: {fn.__module__}.{fn.__name__}")


if __name__ == "__main__":
    main()
