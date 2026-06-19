"""
tenancy.py — Multi-tenant config loader for NemoClaw per-client deployments.

Exports: Tenant, ConfigError, load_tenant, list_tenants.

Each tenant has an isolated config, brain, audit path, and LLM routing policy.
Finance-sensitive tenants (sensitivity in {confidential, restricted}) MUST declare
llm_routing: local — any other value raises ConfigError at load time.

Real/sensitive tenant dirs live under $NEMOCLAW_TENANTS_ROOT (outside this repo).
The tenants/ dir in this repo holds only synthetic samples.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_TENANTS_ROOT = Path(__file__).resolve().parent.parent / "tenants"

_SENSITIVITY_TIERS = ("public", "internal", "confidential", "restricted")
_FINANCE_TIERS = frozenset({"confidential", "restricted"})
_ROUTING_VALUES = frozenset({"local", "frontier"})


class ConfigError(ValueError):
    """Raised when a tenant config violates a hard constraint."""


@dataclass
class Tenant:
    """Resolved, validated tenant configuration.

    data_root may be an absolute path outside the repo.
    brain_path and audit_path default to subdirs of data_root.
    local_model: optional Ollama model tag (e.g. "gemma4:26b") used by route_llm
        when llm_routing == "local". Falls back to OLLAMA_MODEL env / local_client default.
    """

    slug: str
    data_root: str
    llm_routing: str          # "local" | "frontier"
    sensitivity: str          # "public" | "internal" | "confidential" | "restricted"
    mode: str                 # "advisory" | "act"
    thresholds: dict = field(default_factory=dict)
    brain_path: str = ""
    audit_path: str = ""
    local_model: str | None = None   # optional: pin a specific local Ollama model
    ingestion: dict = field(default_factory=dict)  # raw ingestion section from config


def _resolve_paths(slug: str, raw: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    """Resolve data_root, brain_path, audit_path to absolute strings.

    data_root is resolved relative to config_dir if not absolute.
    brain_path and audit_path default to data_root/{brain,audit}.
    """
    data_root_raw = raw.get("data_root", f"data")
    data_root = Path(data_root_raw)
    if not data_root.is_absolute():
        data_root = (config_dir / data_root_raw).resolve()

    brain = Path(raw.get("brain_path", "brain"))
    if not brain.is_absolute():
        brain = data_root / brain

    audit = Path(raw.get("audit_path", "audit"))
    if not audit.is_absolute():
        audit = data_root / audit

    return {
        "data_root": str(data_root),
        "brain_path": str(brain),
        "audit_path": str(audit),
    }


def _validate(tenant: Tenant) -> None:
    """Raise ConfigError on any hard constraint violation.

    Rule: finance-sensitive tenants (confidential/restricted) MUST use local routing.
    A restricted tenant on frontier is the exact mistake this guard prevents.
    """
    if tenant.sensitivity not in _SENSITIVITY_TIERS:
        raise ConfigError(
            f"Tenant '{tenant.slug}': sensitivity '{tenant.sensitivity}' is not valid. "
            f"Must be one of {_SENSITIVITY_TIERS}."
        )
    if tenant.llm_routing not in _ROUTING_VALUES:
        raise ConfigError(
            f"Tenant '{tenant.slug}': llm_routing '{tenant.llm_routing}' is not valid. "
            f"Must be 'local' or 'frontier'."
        )
    if tenant.sensitivity in _FINANCE_TIERS and tenant.llm_routing != "local":
        raise ConfigError(
            f"Tenant '{tenant.slug}': sensitivity='{tenant.sensitivity}' requires "
            f"llm_routing='local', got '{tenant.llm_routing}'. "
            f"Finance-sensitive tenants are structurally prohibited from frontier APIs."
        )


def load_tenant(slug: str, tenants_root: str | None = None) -> Tenant:
    """Load and validate tenant config from tenants/<slug>/config.yaml.

    tenants_root defaults to the repo tenants/ dir but is overridden by
    NEMOCLAW_TENANTS_ROOT env var so real/sensitive tenants live outside the repo.
    """
    root = Path(
        tenants_root
        or os.environ.get("NEMOCLAW_TENANTS_ROOT", str(_REPO_TENANTS_ROOT))
    )
    config_path = root / slug / "config.yaml"
    if not config_path.exists():
        raise ConfigError(f"Tenant config not found: {config_path}")

    with config_path.open() as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    paths = _resolve_paths(slug, raw, config_path.parent)

    tenant = Tenant(
        slug=slug,
        data_root=paths["data_root"],
        llm_routing=raw.get("llm_routing", "local"),
        sensitivity=raw.get("sensitivity", "internal"),
        mode=raw.get("mode", "advisory"),
        thresholds=raw.get("thresholds", {}),
        brain_path=paths["brain_path"],
        audit_path=paths["audit_path"],
        local_model=raw.get("local_model") or None,
        ingestion=raw.get("ingestion") or {},
    )
    _validate(tenant)
    return tenant


def list_tenants(tenants_root: str | None = None) -> list[str]:
    """Return sorted list of tenant slugs found in tenants_root."""
    root = Path(
        tenants_root
        or os.environ.get("NEMOCLAW_TENANTS_ROOT", str(_REPO_TENANTS_ROOT))
    )
    if not root.exists():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    )
