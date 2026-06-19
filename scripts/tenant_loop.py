"""tenant_loop.py — Entry point for `make tenant-loop TENANT=<slug> MODE=weekly|monthly`.

Loads the tenant, runs one ingestion+analysis cycle, and prints a structured summary.
Respects NEMOCLAW_TENANTS_ROOT for real tenant directories outside the repo.

Usage:
  PYTHONPATH=. python3 scripts/tenant_loop.py <slug> <weekly|monthly>
  make tenant-loop TENANT=_sample_str MODE=monthly
"""

from __future__ import annotations

import os
import sys


def _print_summary(slug: str, mode: str, result: dict) -> None:
    """Print a human-readable cycle summary to stdout."""
    print(f"\n=== NemoClaw Ingestion Cycle: {slug} / {mode} ===")
    print(f"  Connector:          {result['connector']}")
    print(f"  Txns fetched:       {result['txns_fetched']}")
    print(f"  Txns total (disk):  {result['txns_total']}")
    print(f"  New findings:       {result['new_findings']}")
    if result.get("report_path"):
        print(f"  Report:             {result['report_path']}")
    if result.get("error"):
        print(f"  Connector error:    {result['error']}")
    print()


def main() -> None:
    """Run cycle for named tenant and mode; exit 1 on config errors."""
    args = sys.argv[1:]
    slug = args[0] if len(args) >= 1 else os.environ.get("TENANT", "")
    mode = args[1] if len(args) >= 2 else os.environ.get("MODE", "monthly")

    if not slug:
        print("Usage: python scripts/tenant_loop.py <slug> <weekly|monthly>", file=sys.stderr)
        sys.exit(1)

    valid_modes = {"weekly", "monthly"}
    if mode not in valid_modes:
        print(f"MODE must be one of {valid_modes}, got '{mode}'", file=sys.stderr)
        sys.exit(1)

    from agent.tenancy import load_tenant, ConfigError
    from analysis.loop import run_cycle

    try:
        tenant = load_tenant(slug)
    except ConfigError as exc:
        print(f"Config error for tenant '{slug}': {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Tenant: {tenant.slug}  |  sensitivity: {tenant.sensitivity}"
        f"  |  routing: {tenant.llm_routing}"
    )

    result = run_cycle(tenant, mode)
    _print_summary(slug, mode, result)


if __name__ == "__main__":
    main()
