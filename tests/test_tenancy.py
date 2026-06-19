"""
test_tenancy.py — Offline tests for agent/tenancy.py, agent/local_client.py,
and the tenant-aware extensions in agent/claw_router.py.

All tests are offline (no network, no .env). Marked with default (no marker)
so they run under `pytest -m "not live"`.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from agent.tenancy import ConfigError, Tenant, load_tenant, list_tenants


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_config(tmp_path: Path, slug: str, **overrides) -> Path:
    """Write a minimal valid tenant config and return the config dir."""
    tenant_dir = tmp_path / slug
    tenant_dir.mkdir(parents=True, exist_ok=True)
    cfg: dict = {
        "llm_routing": "local",
        "sensitivity": "internal",
        "mode": "advisory",
        "data_root": "data",
        "thresholds": {},
    }
    cfg.update(overrides)
    (tenant_dir / "config.yaml").write_text(yaml.dump(cfg))
    return tenant_dir


# ---------------------------------------------------------------------------
# load_tenant — happy path
# ---------------------------------------------------------------------------

def test_load_tenant_returns_tenant_instance(tmp_path):
    """load_tenant returns a Tenant dataclass for a valid config."""
    _write_config(tmp_path, "acme")
    t = load_tenant("acme", tenants_root=str(tmp_path))
    assert isinstance(t, Tenant)


def test_load_tenant_slug_matches(tmp_path):
    """Loaded tenant slug matches the requested slug."""
    _write_config(tmp_path, "acme")
    t = load_tenant("acme", tenants_root=str(tmp_path))
    assert t.slug == "acme"


def test_load_tenant_resolves_data_root_to_absolute(tmp_path):
    """data_root resolved to an absolute path even when declared as a relative string."""
    _write_config(tmp_path, "acme")
    t = load_tenant("acme", tenants_root=str(tmp_path))
    assert Path(t.data_root).is_absolute()


def test_load_tenant_brain_and_audit_under_data_root(tmp_path):
    """brain_path and audit_path default to subdirs of data_root."""
    _write_config(tmp_path, "acme")
    t = load_tenant("acme", tenants_root=str(tmp_path))
    assert t.brain_path.startswith(t.data_root)
    assert t.audit_path.startswith(t.data_root)


def test_load_tenant_reads_thresholds(tmp_path):
    """Threshold dict is preserved from YAML."""
    _write_config(tmp_path, "acme", thresholds={"auto_approve_usd": 100.0})
    t = load_tenant("acme", tenants_root=str(tmp_path))
    assert t.thresholds["auto_approve_usd"] == 100.0


def test_load_tenant_missing_file_raises_config_error(tmp_path):
    """Missing config.yaml raises ConfigError."""
    with pytest.raises(ConfigError, match="not found"):
        load_tenant("ghost", tenants_root=str(tmp_path))


# ---------------------------------------------------------------------------
# load_tenant — frontier guard on restricted sensitivity
# ---------------------------------------------------------------------------

def test_restricted_local_is_valid(tmp_path):
    """restricted + local = valid config, no error."""
    _write_config(tmp_path, "str", sensitivity="restricted", llm_routing="local")
    t = load_tenant("str", tenants_root=str(tmp_path))
    assert t.sensitivity == "restricted"
    assert t.llm_routing == "local"


def test_restricted_frontier_raises_config_error(tmp_path):
    """restricted + frontier raises ConfigError at load time — the hard constraint."""
    _write_config(tmp_path, "str", sensitivity="restricted", llm_routing="frontier")
    with pytest.raises(ConfigError, match="frontier"):
        load_tenant("str", tenants_root=str(tmp_path))


def test_confidential_frontier_raises_config_error(tmp_path):
    """confidential + frontier also raises — same finance-tier rule."""
    _write_config(tmp_path, "fin", sensitivity="confidential", llm_routing="frontier")
    with pytest.raises(ConfigError, match="frontier"):
        load_tenant("fin", tenants_root=str(tmp_path))


def test_public_frontier_is_valid(tmp_path):
    """public + frontier is explicitly allowed."""
    _write_config(tmp_path, "pub", sensitivity="public", llm_routing="frontier")
    t = load_tenant("pub", tenants_root=str(tmp_path))
    assert t.llm_routing == "frontier"


def test_invalid_sensitivity_raises_config_error(tmp_path):
    """An unrecognized sensitivity value raises ConfigError."""
    _write_config(tmp_path, "bad", sensitivity="ultra-secret", llm_routing="local")
    with pytest.raises(ConfigError, match="sensitivity"):
        load_tenant("bad", tenants_root=str(tmp_path))


# ---------------------------------------------------------------------------
# list_tenants
# ---------------------------------------------------------------------------

def test_list_tenants_returns_sorted_slugs(tmp_path):
    """list_tenants returns alphabetically sorted slug list."""
    for slug in ("bravo", "alpha", "charlie"):
        _write_config(tmp_path, slug)
    slugs = list_tenants(tenants_root=str(tmp_path))
    assert slugs == ["alpha", "bravo", "charlie"]


def test_list_tenants_empty_dir_returns_empty(tmp_path):
    """Empty tenants_root returns empty list without error."""
    assert list_tenants(tenants_root=str(tmp_path)) == []


def test_list_tenants_ignores_dirs_without_config(tmp_path):
    """Directories without config.yaml are excluded."""
    _write_config(tmp_path, "valid")
    (tmp_path / "no-config").mkdir()
    slugs = list_tenants(tenants_root=str(tmp_path))
    assert slugs == ["valid"]


# ---------------------------------------------------------------------------
# route_llm — callable selection
# ---------------------------------------------------------------------------

def test_route_llm_local_tenant_returns_call_local(tmp_path):
    """route_llm returns call_local for a local-routing tenant."""
    from agent.claw_router import route_llm
    from agent.local_client import call_local

    _write_config(tmp_path, "str", sensitivity="restricted", llm_routing="local")
    t = load_tenant("str", tenants_root=str(tmp_path))
    assert route_llm(t) is call_local


def test_route_llm_frontier_tenant_returns_call_hermes(tmp_path):
    """route_llm returns call_hermes for a frontier-routing tenant."""
    from agent.claw_router import route_llm
    from agent.hermes_client import call_hermes

    _write_config(tmp_path, "pub", sensitivity="public", llm_routing="frontier")
    t = load_tenant("pub", tenants_root=str(tmp_path))
    assert route_llm(t) is call_hermes


# ---------------------------------------------------------------------------
# assert_no_frontier — runtime guard
# ---------------------------------------------------------------------------

def test_assert_no_frontier_raises_for_local_tenant(tmp_path):
    """assert_no_frontier raises RuntimeError when tenant is local-routed."""
    from agent.claw_router import assert_no_frontier

    _write_config(tmp_path, "str", sensitivity="restricted", llm_routing="local")
    t = load_tenant("str", tenants_root=str(tmp_path))
    with pytest.raises(RuntimeError, match="structurally prohibited"):
        assert_no_frontier(t)


def test_assert_no_frontier_raises_for_restricted_even_if_frontier_label(tmp_path):
    """Restricted tenants can't be labelled frontier (ConfigError fires at load),
    but if a Tenant is constructed directly with mismatched values the guard still fires."""
    from agent.claw_router import assert_no_frontier

    # Construct directly, bypassing load_tenant validation, to test the runtime guard.
    t = Tenant(
        slug="bypass",
        data_root="/tmp/bypass",
        llm_routing="frontier",
        sensitivity="restricted",
        mode="advisory",
    )
    with pytest.raises(RuntimeError, match="structurally prohibited"):
        assert_no_frontier(t)


def test_assert_no_frontier_passes_for_frontier_public(tmp_path):
    """assert_no_frontier does not raise for a public frontier tenant."""
    from agent.claw_router import assert_no_frontier

    _write_config(tmp_path, "pub", sensitivity="public", llm_routing="frontier")
    t = load_tenant("pub", tenants_root=str(tmp_path))
    assert_no_frontier(t)  # must not raise


# ---------------------------------------------------------------------------
# call_local — no-network mock behaviour
# ---------------------------------------------------------------------------

def test_call_local_returns_mock_string_when_ollama_unreachable(monkeypatch):
    """call_local returns the [local-mock] prefix string when Ollama is down.

    No network call — monkeypatched httpx.Client raises immediately.
    """
    import httpx
    from agent.local_client import call_local, _MOCK_PREFIX

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "Client", lambda **kw: _RaisingClient(_raise))

    result = call_local([{"role": "user", "content": "hello"}])
    assert result.startswith(_MOCK_PREFIX)


def test_call_local_does_not_raise_on_network_error(monkeypatch):
    """call_local never propagates exceptions — it always returns a string."""
    import httpx
    from agent.local_client import call_local

    def _raise(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "Client", lambda **kw: _RaisingClient(_raise))

    result = call_local([{"role": "user", "content": "ping"}])
    assert isinstance(result, str)


class _RaisingClient:
    """Minimal httpx.Client stand-in that raises on any method call."""

    def __init__(self, exc_factory):
        self._exc = exc_factory

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def post(self, *args, **kwargs):
        raise self._exc()

    def get(self, *args, **kwargs):
        raise self._exc()


# ---------------------------------------------------------------------------
# Sample tenant smoke test
# ---------------------------------------------------------------------------

def test_sample_str_tenant_loads():
    """The committed _sample_str tenant loads without error."""
    t = load_tenant("_sample_str")
    assert t.slug == "_sample_str"
    assert t.llm_routing == "local"
    assert t.sensitivity == "restricted"


def test_sample_str_data_csv_exists():
    """The sample transactions CSV is present in the repo."""
    from agent.tenancy import _REPO_TENANTS_ROOT
    csv = _REPO_TENANTS_ROOT / "_sample_str" / "data" / "transactions.csv"
    assert csv.exists(), f"Sample CSV missing: {csv}"
