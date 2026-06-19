"""
test_gbrain_client.py — Unit tests for gbrain/gbrain_client.py with a mocked MCP session.

Covers:
    - gbrain_available() returns False when GBRAIN_MCP_CMD is unset
    - gbrain_available() returns False when mcp is unimportable (simulated)
    - writes are forwarded to MCP session when available (mocked)
    - KnowledgeGraph._mirror_vendor / _mirror_payment swallow GBrainError without raising
    - search_pages and read_page parse session responses correctly
"""

from __future__ import annotations

import os
import sys
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_result(*, is_error: bool = False, text: str = "") -> MagicMock:
    """Build a fake CallToolResult-like object."""
    result = MagicMock()
    result.isError = is_error
    text_content = MagicMock()
    text_content.text = text
    result.content = [text_content]
    return result


# ---------------------------------------------------------------------------
# gbrain_available
# ---------------------------------------------------------------------------

class TestGbrainAvailable:
    """gbrain_available() reflects env + import state."""

    def test_false_when_cmd_unset(self) -> None:
        """Returns False when GBRAIN_MCP_CMD is absent."""
        from gbrain.gbrain_client import gbrain_available
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GBRAIN_MCP_CMD", None)
            assert gbrain_available() is False

    def test_false_when_mcp_unimportable(self) -> None:
        """Returns False when GBRAIN_MCP_CMD is set but mcp cannot be imported."""
        with patch.dict(os.environ, {"GBRAIN_MCP_CMD": "gbrain serve"}):
            with patch.dict(sys.modules, {"mcp": None}):
                # Reload module so _GBRAIN_MCP_CMD is re-read
                import importlib
                import gbrain.gbrain_client as mod
                importlib.reload(mod)
                # mcp in sys.modules is None → ImportError on import
                assert mod.gbrain_available() is False
                importlib.reload(mod)  # restore

    def test_true_when_cmd_set_and_mcp_importable(self) -> None:
        """Returns True when GBRAIN_MCP_CMD is set and mcp is importable."""
        with patch.dict(os.environ, {"GBRAIN_MCP_CMD": "gbrain serve"}):
            import importlib
            import gbrain.gbrain_client as mod
            importlib.reload(mod)
            # mcp is actually installed in this venv
            assert mod.gbrain_available() is True
            importlib.reload(mod)  # restore


# ---------------------------------------------------------------------------
# write_vendor_page / write_payment_page (mocked session)
# ---------------------------------------------------------------------------

class TestWriteVendorPage:
    """write_vendor_page forwards a put_page call with correct slug and content."""

    def test_forwards_put_page(self) -> None:
        """put_page is called with the expected slug and content contains vendor name."""
        from gbrain.gbrain_client import write_vendor_page

        mock_result = _make_tool_result(is_error=False, text="ok")

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            assert tool == "put_page"
            assert args["slug"].startswith("nemoclaw/vendors/")
            assert "acme" in args["slug"]
            assert "Acme Corp" in args["content"]
            assert "SaaS" in args["content"]
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            write_vendor_page("acme", "Acme Corp", "SaaS")

    def test_raises_gbrain_error_on_is_error(self) -> None:
        """Raises GBrainError when the server returns isError=True."""
        from gbrain.gbrain_client import GBrainError, write_vendor_page

        mock_result = _make_tool_result(is_error=True, text="internal server error")

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            with pytest.raises(GBrainError, match="put_page returned isError"):
                write_vendor_page("badvendor", "Bad Vendor", "Other")


class TestWritePaymentPage:
    """write_payment_page forwards a put_page call with correct slug and content."""

    def test_forwards_put_page(self) -> None:
        """put_page is called with payment slug and content contains amount + date."""
        from gbrain.gbrain_client import write_payment_page

        mock_result = _make_tool_result(is_error=False, text="ok")

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            assert tool == "put_page"
            assert "nemoclaw/payments" in args["slug"]
            assert "42.50" in args["content"]
            assert "2024-01-15" in args["content"]
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            write_payment_page("acme", "Acme Corp", 42.50, "2024-01-15", "SaaS", None)


# ---------------------------------------------------------------------------
# search_pages / read_page
# ---------------------------------------------------------------------------

class TestSearchPages:
    """search_pages forwards the search call and returns parsed results."""

    def test_returns_raw_results(self) -> None:
        """Returned list contains one entry per content item from the server."""
        from gbrain.gbrain_client import search_pages

        item1 = MagicMock()
        item1.text = "vendors/acme — Acme Corp"
        item2 = MagicMock()
        item2.text = "vendors/beta — Beta LLC"
        mock_result = MagicMock()
        mock_result.isError = False
        mock_result.content = [item1, item2]

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            assert tool == "search"
            assert args["query"] == "acme"
            assert args["limit"] == 5
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            results = search_pages("acme", limit=5)

        assert len(results) == 2
        assert results[0]["raw"] == "vendors/acme — Acme Corp"

    def test_raises_on_is_error(self) -> None:
        """Raises GBrainError when search returns isError=True."""
        from gbrain.gbrain_client import GBrainError, search_pages

        mock_result = _make_tool_result(is_error=True, text="search backend error")

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            with pytest.raises(GBrainError, match="search returned isError"):
                search_pages("anything")


class TestReadPage:
    """read_page retrieves a page by slug."""

    def test_returns_content_on_success(self) -> None:
        """Returns concatenated text content when page exists."""
        from gbrain.gbrain_client import read_page

        item = MagicMock()
        item.text = "# Acme Corp\n\nVendor category: SaaS.\n"
        mock_result = MagicMock()
        mock_result.isError = False
        mock_result.content = [item]

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            assert tool == "get_page"
            assert args["slug"] == "nemoclaw/vendors/acme"
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            content = read_page("nemoclaw/vendors/acme")

        assert content is not None
        assert "Acme Corp" in content

    def test_returns_none_on_not_found(self) -> None:
        """Returns None when the server says 'not found'."""
        from gbrain.gbrain_client import read_page

        mock_result = _make_tool_result(is_error=True, text="not found")

        async def fake_stdio_call(tool: str, args: dict[str, Any]) -> Any:
            return mock_result

        with patch("gbrain.gbrain_client._stdio_call", side_effect=fake_stdio_call):
            result = read_page("nemoclaw/vendors/missing")

        assert result is None


# ---------------------------------------------------------------------------
# KnowledgeGraph mirror integration (no GBrain crash-through)
# ---------------------------------------------------------------------------

class TestKnowledgeGraphMirror:
    """Mirror calls in KnowledgeGraph swallow GBrainError and never crash."""

    def test_add_vendor_proceeds_on_gbrain_error(self) -> None:
        """add_vendor succeeds in-memory even if GBrain write_vendor_page raises."""
        from gbrain.gbrain_client import GBrainError
        from gbrain.knowledge_graph import KnowledgeGraph

        with patch("gbrain.gbrain_client.gbrain_available", return_value=True):
            with patch("gbrain.gbrain_client.write_vendor_page", side_effect=GBrainError("conn refused")):
                g = KnowledgeGraph()
                g.add_vendor("Acme", category="SaaS")  # must not raise

        assert g.is_known_vendor("Acme")

    def test_record_payment_proceeds_on_gbrain_error(self) -> None:
        """record_payment succeeds in-memory even if GBrain write_payment_page raises."""
        from gbrain.gbrain_client import GBrainError
        from gbrain.knowledge_graph import KnowledgeGraph

        with patch("gbrain.gbrain_client.gbrain_available", return_value=True):
            with patch("gbrain.gbrain_client.write_vendor_page", return_value=None):
                with patch("gbrain.gbrain_client.write_payment_page", side_effect=GBrainError("timeout")):
                    g = KnowledgeGraph()
                    g.record_payment("Acme", 100.0, "2024-01-01", category="SaaS")

        assert g.vendor_history("Acme") == [100.0]

    def test_no_gbrain_calls_when_unavailable(self) -> None:
        """No MCP calls are made when gbrain_available() returns False."""
        from gbrain.knowledge_graph import KnowledgeGraph

        with patch("gbrain.gbrain_client.gbrain_available", return_value=False):
            with patch("gbrain.gbrain_client.write_vendor_page") as mock_write:
                g = KnowledgeGraph()
                g.add_vendor("Acme", category="SaaS")
                mock_write.assert_not_called()
