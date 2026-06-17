"""
knowledge_graph.py — In-memory + JSON-persisted knowledge graph for SMB vendor intelligence.

Exports:
    KnowledgeGraph          — main graph class (add_vendor, record_payment, load_records, query, persist)
    build_graph_from_invoices — convenience: ingest_to_graph_records then load_records

Swap note: if GBRAIN_MCP_URL env var is set, a production deployment would instantiate a real
GBrain MCP client (Garry Tan's PGLite-backed server) instead of this in-memory mock. The public
API surface here mirrors the GBrain contract so that swap is a single localized change.
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

from gbrain.invoice_ingestion import ingest_to_graph_records

#COMPLETION_DRIVE: GBRAIN_MCP_URL presence is documented but not acted on; mock is always used here
_GBRAIN_MCP_URL = os.environ.get("GBRAIN_MCP_URL")


def _normalize_name(name: str) -> str:
    """Return lowercase stripped vendor name for case-insensitive matching."""
    return name.lower().strip()


class KnowledgeGraph:
    """In-memory vendor knowledge graph with JSON persistence.

    Nodes: company:self (singleton) + one vendor node per unique vendor.
    Edges: 'paid' edges from company:self to vendor nodes.
    """

    def __init__(self) -> None:
        """Initialize empty graph with a singleton company node."""
        self._vendors: dict[str, dict] = {}       # normalized_name -> node attrs
        self._payments: dict[str, list[dict]] = {} # normalized_name -> sorted edge list

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_vendor(self, name: str, category: str | None = None, **attrs) -> None:
        """Upsert a vendor node; preserves existing category if not supplied."""
        key = _normalize_name(name)
        existing = self._vendors.get(key, {})
        node = {
            "id": f"vendor:{key}",
            "label": name,
            "type": "vendor",
            "category": category or existing.get("category") or "Other",
        }
        node.update(attrs)
        self._vendors[key] = node
        self._payments.setdefault(key, [])

    def record_payment(
        self,
        vendor: str,
        amount: float,
        date: str,
        category: str | None = None,
        anomaly_flag: bool | None = None,
    ) -> None:
        """Append a paid edge; auto-creates vendor node if absent."""
        key = _normalize_name(vendor)
        if key not in self._vendors:
            self.add_vendor(vendor, category=category)
        edge = {
            "source": "company:self",
            "target": f"vendor:{key}",
            "amount": float(amount),
            "date": date,
            "category": category or self._vendors[key].get("category") or "Other",
            "anomaly_flag": anomaly_flag,
        }
        self._payments[key].append(edge)
        self._payments[key].sort(key=lambda e: e["date"])

    def load_records(self, records: list[dict]) -> None:
        """Ingest invoice_ingestion graph records (vendor nodes + paid edges)."""
        for rec in records:
            if rec.get("record_type") == "node" and rec.get("node_type") == "vendor":
                self.add_vendor(
                    rec["label"],
                    category=rec.get("category"),
                )
            elif rec.get("record_type") == "edge" and rec.get("edge_type") == "paid":
                target_id = rec.get("target", "")
                # target is "vendor:<normalized_name>"; extract the label from stored nodes
                vendor_key = target_id.removeprefix("vendor:")
                label = self._vendors.get(vendor_key, {}).get("label") or vendor_key
                self.record_payment(
                    vendor=label,
                    amount=rec["amount"],
                    date=rec["date"],
                    category=rec.get("category"),
                    anomaly_flag=rec.get("anomaly_flag"),
                )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def is_known_vendor(self, name: str) -> bool:
        """Return True if vendor exists in graph (case-insensitive)."""
        return _normalize_name(name) in self._vendors

    def vendor_history(self, name: str) -> list[float]:
        """Return payment amounts for vendor in ascending date order."""
        key = _normalize_name(name)
        return [e["amount"] for e in self._payments.get(key, [])]

    def expected_range(self, name: str) -> tuple[float, float] | None:
        """Return (mean-2std, mean+2std) for vendor; None if fewer than 2 payments."""
        amounts = self.vendor_history(name)
        if len(amounts) < 2:
            return None
        mean = statistics.mean(amounts)
        std = statistics.stdev(amounts)
        return (mean - 2 * std, mean + 2 * std)

    def nodes(self) -> list[dict]:
        """Return all nodes for force-graph rendering (company:self + vendors)."""
        company_node = {
            "id": "company:self",
            "label": "Company",
            "type": "company",
            "category": None,
        }
        return [company_node] + list(self._vendors.values())

    def edges(self) -> list[dict]:
        """Return all paid edges for force-graph rendering."""
        result: list[dict] = []
        for edges in self._payments.values():
            result.extend(edges)
        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize graph to a JSON-safe dict."""
        return {
            "vendors": list(self._vendors.values()),
            "payments": {k: v for k, v in self._payments.items()},
        }

    def save(self, path: str | Path) -> None:
        """Write graph to JSON file at path."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeGraph":
        """Restore a KnowledgeGraph from a JSON file written by save()."""
        data = json.loads(Path(path).read_text())
        g = cls()
        for node in data.get("vendors", []):
            g.add_vendor(node["label"], category=node.get("category"))
        for key, edges in data.get("payments", {}).items():
            for edge in edges:
                g.record_payment(
                    vendor=g._vendors.get(key, {}).get("label") or key,
                    amount=edge["amount"],
                    date=edge["date"],
                    category=edge.get("category"),
                    anomaly_flag=edge.get("anomaly_flag"),
                )
        return g


# ------------------------------------------------------------------
# Convenience
# ------------------------------------------------------------------

def build_graph_from_invoices(invoices: list[dict]) -> KnowledgeGraph:
    """Ingest raw invoice dicts and return a populated KnowledgeGraph."""
    records = ingest_to_graph_records(invoices)
    g = KnowledgeGraph()
    g.load_records(records)
    return g
