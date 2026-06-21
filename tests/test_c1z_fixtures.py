"""tests/test_c1z_fixtures.py: unit tests for the bundled Baton .c1z fixture.

Verifies the generated .c1z is a real gzipped SQLite in Baton's v1_* schema with
the STR-org entitlement graph, and that carryall_baton.BatonBackend reads it for
real grant matching when the optional package is installed. No network, no SaaS.
"""
from __future__ import annotations

import gzip
import sqlite3

from control_plane.c1z_fixtures import (
    PRINCIPAL_MAP,
    fixture_path,
    generate_c1z,
)


def _baton_importable() -> bool:
    """Return True when both authority_runtime and carryall_baton import."""
    try:
        import authority_runtime  # noqa: F401
        import carryall_baton  # noqa: F401

        return True
    except ImportError:
        return False


def test_generate_c1z_writes_gzipped_sqlite(tmp_path) -> None:
    """generate_c1z writes a gzip-magic file decompressing to a SQLite database."""
    dest = tmp_path / "str_org.c1z"
    path = generate_c1z(dest)
    assert path == str(dest)
    with open(dest, "rb") as fh:
        assert fh.read(2) == b"\x1f\x8b"  # gzip magic


def test_c1z_has_baton_schema_tables(tmp_path) -> None:
    """The decompressed .c1z has v1_resources, v1_entitlements, v1_grants."""
    dest = tmp_path / "str_org.c1z"
    generate_c1z(dest)
    sqlite_path = tmp_path / "decompressed.sqlite"
    with gzip.open(dest, "rb") as src, open(sqlite_path, "wb") as out:
        out.write(src.read())
    conn = sqlite3.connect(str(sqlite_path))
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        conn.close()
    assert {"v1_resources", "v1_entitlements", "v1_grants"} <= names


def test_c1z_has_str_org_grants(tmp_path) -> None:
    """The .c1z carries the cleaner, platform, and owner grants."""
    dest = tmp_path / "str_org.c1z"
    generate_c1z(dest)
    sqlite_path = tmp_path / "decompressed.sqlite"
    with gzip.open(dest, "rb") as src, open(sqlite_path, "wb") as out:
        out.write(src.read())
    conn = sqlite3.connect(str(sqlite_path))
    try:
        grant_count = conn.execute("SELECT COUNT(*) FROM v1_grants").fetchone()[0]
        ent_ids = {
            row[0] for row in conn.execute("SELECT external_id FROM v1_entitlements")
        }
    finally:
        conn.close()
    assert grant_count == 4
    assert "card:issue:cleaning" in ent_ids
    assert "str:price" in ent_ids
    assert "str:aeo-audit" in ent_ids


def test_principal_map_covers_str_agents() -> None:
    """PRINCIPAL_MAP binds the cleaner and platform agent ids to baton principals."""
    assert PRINCIPAL_MAP["cleaner-subagent"] == "cleaner-subagent"
    assert PRINCIPAL_MAP["str-platform-agent"] == "str-platform-agent"


def test_fixture_path_generates_on_demand() -> None:
    """fixture_path returns a real .c1z; calling twice is stable."""
    p1 = fixture_path()
    p2 = fixture_path()
    assert p1 == p2
    with open(p1, "rb") as fh:
        assert fh.read(2) == b"\x1f\x8b"


def test_batonbackend_reads_fixture_grants() -> None:
    """BatonBackend.check_access ALLOWs a real grant from the bundled fixture."""
    if not _baton_importable():
        import pytest

        pytest.skip("authority_runtime / carryall_baton not installed")

    import authority_runtime
    from carryall_baton import BatonBackend

    backend = BatonBackend(fixture_path(), agent_to_principal=PRINCIPAL_MAP)
    assert "platform" in backend.list_vaults()

    priv, _pub = authority_runtime.generate_key_pair()
    envelope = authority_runtime.create_simple_envelope(
        agent_id="str-platform-agent",
        scopes=["nhi:placeholder"],
        private_key=priv,
    )
    result = backend.check_access(
        envelope, action="price", uri="slos://vaults/platform/str"
    )
    assert result.decision == result.decision.ALLOW
