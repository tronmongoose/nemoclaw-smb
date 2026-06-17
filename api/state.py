"""Module-level singleton state for the demo API.

The knowledge graph is built once at import time from seed invoices and shared
across all route handlers within the process lifetime.

Exports:
    graph   — populated KnowledgeGraph instance
"""

#GLOBAL-STATE: demo in-process graph; acceptable for a single-process hackathon deployment
from fixtures.seed_data import seed_invoices
from gbrain.knowledge_graph import build_graph_from_invoices

graph = build_graph_from_invoices(seed_invoices())
