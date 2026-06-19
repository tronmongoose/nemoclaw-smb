"""
gbrain_client.py — MCP client for the GBrain knowledge-graph backend.

Exports:
    GBrainError         — typed error; callers catch this and fall back to in-memory
    gbrain_available    — True when GBRAIN_MCP_CMD or GBRAIN_MCP_URL is set and mcp importable
    write_vendor_page   — upsert a vendor node as a GBrain page
    write_payment_page  — write a payment edge as a GBrain page
    search_pages        — search pages by query string; returns list of slug dicts
    read_page           — read a single page by slug; returns content string or None

Configuration (from environment):
    GBRAIN_MCP_CMD  — shell command to launch the MCP stdio server.
                      #COMPLETION_DRIVE: expected value when bun is installed:
                        "bun /path/to/gbrain/src/cli.ts serve"
                        or after `npm install -g github:garrytan/gbrain` and bun on PATH.
    GBRAIN_MCP_URL  — HTTP MCP URL (e.g. http://localhost:4000/mcp); if set, used for HTTP transport.
                      #COMPLETION_DRIVE: HTTP transport (SSE/streamable-http) via mcp is not yet
                        implemented in this client. Only stdio is wired today. If only
                        GBRAIN_MCP_URL is set without GBRAIN_MCP_CMD, gbrain_available() returns
                        False. Set GBRAIN_MCP_CMD to the gbrain stdio command to activate.

MCP tool names used (from garrytan/gbrain master src/core/operations.ts):
    put_page   — write/update a page; params: slug (str), content (str)
    get_page   — read a page by slug; params: slug (str)
    search     — keyword+vector search; params: query (str), limit (int)

All public functions are synchronous wrappers around asyncio.run().
They are intended to be called from non-async code paths in KnowledgeGraph.
Do NOT call from inside an already-running event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_GBRAIN_MCP_CMD = os.environ.get("GBRAIN_MCP_CMD", "")
_GBRAIN_MCP_URL = os.environ.get("GBRAIN_MCP_URL", "")


class GBrainError(Exception):
    """Raised when a GBrain MCP operation fails; callers should fall back gracefully."""


def gbrain_available() -> bool:
    """Return True when a stdio MCP command is configured and the mcp package is importable."""
    if not _GBRAIN_MCP_CMD:
        return False
    try:
        import mcp  # noqa: F401 — lazy import; not used here, just verifying presence
        return True
    except ImportError:
        return False


def _slug_for_vendor(vendor_key: str) -> str:
    """Return a GBrain page slug for a vendor node."""
    safe = re.sub(r"[^a-z0-9_-]", "-", vendor_key.lower())
    return f"nemoclaw/vendors/{safe}"


def _slug_for_payment(vendor_key: str, date: str, amount: float) -> str:
    """Return a GBrain page slug for a payment edge (vendor + date + amount hash)."""
    safe = re.sub(r"[^a-z0-9_-]", "-", vendor_key.lower())
    amount_tag = f"{int(amount * 100):010d}"
    return f"nemoclaw/payments/{safe}/{date}/{amount_tag}"


async def _stdio_call(tool: str, args: dict[str, Any]) -> Any:
    """Run one MCP tool call over a short-lived stdio session.

    Opens the server process, initializes the session, calls the tool, closes.
    Each call pays process startup cost (~100–300ms for Node).
    #COMPLETION_DRIVE: connection pooling would reduce this; acceptable for
      the mirroring use case where writes are not on the hot path.
    """
    from mcp import ClientSession, StdioServerParameters, stdio_client

    parts = _GBRAIN_MCP_CMD.split()
    params = StdioServerParameters(command=parts[0], args=parts[1:])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
    return result


def _run(coro: Any) -> Any:
    """Execute a coroutine synchronously; raises GBrainError on any exception."""
    try:
        return asyncio.run(coro)
    except Exception as exc:  # noqa: BLE001
        raise GBrainError(str(exc)) from exc


def write_vendor_page(vendor_key: str, label: str, category: str) -> None:
    """Upsert a vendor node as a GBrain page under nemoclaw/vendors/<key>.

    Content is minimal YAML frontmatter + prose so GBrain can index and search it.
    Raises GBrainError on any transport or tool failure.
    """
    slug = _slug_for_vendor(vendor_key)
    content = (
        f"---\ntitle: {label}\ncategory: {category}\ntype: vendor\n---\n\n"
        f"# {label}\n\nVendor category: {category}.\n"
    )
    result = _run(_stdio_call("put_page", {"slug": slug, "content": content}))
    if result.isError:
        raise GBrainError(f"put_page returned isError for vendor {slug}: {result.content}")


def write_payment_page(
    vendor_key: str,
    label: str,
    amount: float,
    date: str,
    category: str,
    anomaly_flag: bool | None,
) -> None:
    """Write a payment edge as a GBrain page under nemoclaw/payments/<vendor>/<date>/<amt>.

    Raises GBrainError on any transport or tool failure.
    """
    slug = _slug_for_payment(vendor_key, date, amount)
    anomaly_str = str(anomaly_flag) if anomaly_flag is not None else "unknown"
    content = (
        f"---\ntitle: Payment to {label} on {date}\n"
        f"vendor: {label}\nvendor_id: vendor:{vendor_key}\n"
        f"amount: {amount}\ndate: {date}\ncategory: {category}\n"
        f"anomaly_flag: {anomaly_str}\ntype: payment\n---\n\n"
        f"# Payment: {label} — {date}\n\n"
        f"Amount: ${amount:.2f}. Category: {category}. Anomaly: {anomaly_str}.\n"
    )
    result = _run(_stdio_call("put_page", {"slug": slug, "content": content}))
    if result.isError:
        raise GBrainError(f"put_page returned isError for payment {slug}: {result.content}")


def search_pages(query: str, limit: int = 10) -> list[dict[str, str]]:
    """Search GBrain for pages matching query; returns list of {slug, title} dicts.

    Raises GBrainError on transport failure.
    #COMPLETION_DRIVE: response content shape is derived from GBrain tool-defs doc
      reading; verify against a live server response when bun is available.
    """
    result = _run(_stdio_call("search", {"query": query, "limit": limit}))
    if result.isError:
        raise GBrainError(f"search returned isError for query {query!r}: {result.content}")
    # content is a list of TextContent; we return the raw text for callers to parse
    out: list[dict[str, str]] = []
    for item in result.content:
        text = getattr(item, "text", "")
        out.append({"raw": text})
    return out


def read_page(slug: str) -> str | None:
    """Read a GBrain page by slug; returns page content string or None if not found.

    Raises GBrainError on transport failure (not on 404 — returns None).
    """
    result = _run(_stdio_call("get_page", {"slug": slug}))
    if result.isError:
        # Extract text from content items before stringifying for reliable matching
        text_parts = [getattr(c, "text", "") for c in result.content]
        content_str = " ".join(text_parts) or str(result.content)
        if "not found" in content_str.lower() or "404" in content_str:
            return None
        raise GBrainError(f"get_page returned isError for slug {slug!r}: {content_str}")
    return "\n".join(getattr(c, "text", "") for c in result.content)
