"""base.py — Connector Protocol and factory for NemoClaw ingestion.

Exports: Connector (Protocol), ConnectorError, get_connector

The Connector protocol is the only surface connectors must implement.
State dicts are opaque per-connector (e.g. {"cursor": "..."} for Plaid).
get_connector reads tenant.connector (default "manual_folder") and returns
the matching implementation; raises ConnectorError on unknown values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from agent.tenancy import Tenant

_DEFAULT_CONNECTOR = "manual_folder"
_KNOWN_CONNECTORS = frozenset({"manual_folder", "plaid"})


class ConnectorError(RuntimeError):
    """Typed error raised for connector configuration or runtime failures.

    The loop catches this to skip/report without crashing the full cycle.
    """


@runtime_checkable
class Connector(Protocol):
    """Protocol every connector must satisfy.

    fetch returns (new_transactions, updated_state).
    - new_transactions: list of normalized dicts {date, vendor, amount, direction, category, source}
    - updated_state: opaque dict persisted to connector.json between runs
    """

    def fetch(
        self,
        tenant: "Tenant",
        state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch transactions since last run; return txns + updated state."""
        ...


def get_connector(tenant: "Tenant") -> "Connector":
    """Return a connector instance based on tenant.connector config field.

    Falls back to manual_folder when the field is absent or empty.
    Raises ConnectorError for unknown connector names.
    """
    raw = getattr(tenant, "connector", None)
    if not raw:
        raw = (tenant.ingestion or {}).get("connector", _DEFAULT_CONNECTOR)
    name = (raw or _DEFAULT_CONNECTOR).strip().lower()

    if name == "manual_folder":
        from connectors.manual_folder import ManualFolderConnector
        return ManualFolderConnector()

    if name == "plaid":
        from connectors.plaid_conn import PlaidConnector
        return PlaidConnector()

    raise ConnectorError(
        f"Unknown connector '{name}' for tenant '{tenant.slug}'. "
        f"Valid values: {sorted(_KNOWN_CONNECTORS)}"
    )
