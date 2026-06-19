"""connectors — Pluggable data-source adapters for NemoClaw monthly ingestion.

Exports: Connector (Protocol), ConnectorError, get_connector

Each connector implements fetch(tenant, state) -> (transactions, updated_state).
State is opaque JSON-serializable data persisted between runs (e.g. Plaid cursor).
get_connector(tenant) picks the implementation from tenant config connector field.
"""

from connectors.base import Connector, ConnectorError, get_connector

__all__ = ["Connector", "ConnectorError", "get_connector"]
