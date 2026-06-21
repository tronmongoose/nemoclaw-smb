"""control_plane/c1z_fixtures: bundled Baton .c1z for the STR org entitlement graph.

A .c1z is a gzipped SQLite entitlement graph in Baton's v1_* schema. This package
generates a small, real .c1z that carryall_baton.BatonBackend.check_access reads for
real grant matching. No ConductorOne SaaS tenant is required to produce or read it.

Schema (verified against carryall_baton 0.1.0 c1z.C1ZReader):
    v1_resources(resource_type_id, id, external_id,
                 parent_resource_type_id, parent_resource_id, sync_id)
    v1_entitlements(id, resource_type_id, resource_id, external_id, sync_id)
    v1_grants(principal_resource_type_id, principal_resource_id,
              resource_type_id, resource_id, entitlement_id, sync_id)

Grant-match contract (verified against carryall_baton 0.1.0 backend._action_matches):
    A requested action matches an entitlement when the action equals the last
    ':'-segment of the entitlement external_id (or that segment is admin/maintain).
    Target resources use 'vault/resource' external_id so split_external_id yields
    (vault, resource); URIs are 'slos://vaults/{vault}/{resource}'.

Public API:
    fixture_path() -> str
        Path to the bundled .c1z, generating it on first call if absent.

    generate_c1z(dest_path) -> str
        Write the STR-org .c1z to dest_path and return it.

    PRINCIPAL_MAP -> dict[str, str]
        agent_id -> baton principal external_id, for BatonBackend(agent_to_principal=).
"""
from __future__ import annotations

import gzip
import sqlite3
import tempfile
from pathlib import Path

_FIXTURE_C1Z = Path(__file__).parent / "str_org.c1z"
_SYNC_ID = "sync-str-org-001"

# agent_id -> baton principal external_id. The BatonBackend consults baton grants
# only for agents present here, so an agent authorized in baton but whose envelope
# lacks the per-vault scope is still allowed via the grant graph.
PRINCIPAL_MAP: dict[str, str] = {
    "cleaner-subagent": "cleaner-subagent",
    "str-platform-agent": "str-platform-agent",
    "owner-agent": "owner-agent",
}

# (resource_type_id, id, external_id). Principals are 'user' resources.
_PRINCIPALS = [
    ("user", "u-cleaner", "cleaner-subagent"),
    ("user", "u-platform", "str-platform-agent"),
    ("user", "u-owner", "owner-agent"),
]

# Target resources. external_id 'vault/resource' -> split_external_id (vault, resource).
_RESOURCES = [
    ("vault", "r-cards", "cards/cleaning"),
    ("vault", "r-platform", "platform/str"),
    ("vault", "r-properties", "properties/clementine"),
]

# Entitlements. The last ':'-segment of external_id is the matchable action.
_ENTITLEMENTS = [
    ("e-card-issue", "vault", "r-cards", "card:issue:cleaning"),
    ("e-str-price", "vault", "r-platform", "str:price"),
    ("e-str-aeo", "vault", "r-platform", "str:aeo-audit"),
    ("e-prop-owner", "vault", "r-properties", "property:owner"),
]

# (principal_resource_id, resource_id, entitlement_id). All principals are 'user'.
_GRANTS = [
    ("u-cleaner", "r-cards", "e-card-issue"),
    ("u-platform", "r-platform", "e-str-price"),
    ("u-platform", "r-platform", "e-str-aeo"),
    ("u-owner", "r-properties", "e-prop-owner"),
]


def _write_schema(conn: sqlite3.Connection) -> None:
    """Create the three Baton v1_* tables the C1ZReader queries."""
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE v1_resources (resource_type_id TEXT, id TEXT, external_id TEXT, "
        "parent_resource_type_id TEXT, parent_resource_id TEXT, sync_id TEXT)"
    )
    cur.execute(
        "CREATE TABLE v1_entitlements (id TEXT, resource_type_id TEXT, "
        "resource_id TEXT, external_id TEXT, sync_id TEXT)"
    )
    cur.execute(
        "CREATE TABLE v1_grants (principal_resource_type_id TEXT, "
        "principal_resource_id TEXT, resource_type_id TEXT, resource_id TEXT, "
        "entitlement_id TEXT, sync_id TEXT)"
    )


def _populate(conn: sqlite3.Connection) -> None:
    """Insert the STR-org principals, resources, entitlements, and grants."""
    cur = conn.cursor()
    for rt, rid, ext in _PRINCIPALS + _RESOURCES:
        cur.execute(
            "INSERT INTO v1_resources VALUES (?,?,?,?,?,?)",
            (rt, rid, ext, None, None, _SYNC_ID),
        )
    for eid, rt, rid, ext in _ENTITLEMENTS:
        cur.execute(
            "INSERT INTO v1_entitlements VALUES (?,?,?,?,?)",
            (eid, rt, rid, ext, _SYNC_ID),
        )
    for prid, rid, eid in _GRANTS:
        cur.execute(
            "INSERT INTO v1_grants VALUES (?,?,?,?,?,?)",
            ("user", prid, "vault", rid, eid, _SYNC_ID),
        )
    conn.commit()


def generate_c1z(dest_path: str | Path) -> str:
    """Write the STR-org .c1z (gzipped SQLite) to dest_path and return its path."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(str(tmp_path))
        try:
            _write_schema(conn)
            _populate(conn)
        finally:
            conn.close()
        dest = Path(dest_path)
        with open(tmp_path, "rb") as src, gzip.open(dest, "wb") as dst:
            dst.write(src.read())
        return str(dest)
    finally:
        tmp_path.unlink(missing_ok=True)


def fixture_path() -> str:
    """Return the bundled .c1z path, generating it on first call if absent."""
    if not _FIXTURE_C1Z.exists():
        generate_c1z(_FIXTURE_C1Z)
    return str(_FIXTURE_C1Z)


if __name__ == "__main__":  # pragma: no cover
    print(generate_c1z(_FIXTURE_C1Z))
