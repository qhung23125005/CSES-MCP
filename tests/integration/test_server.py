"""
Integration tests for the CSES MCP server.
"""

import functools
from pathlib import Path

import httpx
import pytest
from fastmcp import Client

from src.cses_mcp.config.settings import settings
from src.cses_mcp.server import mcp

FIXTURE_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_problemset_sample.html"
).read_text(encoding="utf-8")


class TestServerIntegration:
    """Integration tests exercising the running MCP server in-process."""

    @pytest.mark.asyncio
    async def test_tools_are_registered(self):
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]

        assert "fetch_problems" in tool_names

    @pytest.mark.asyncio
    async def test_fetch_problems_tool(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=FIXTURE_HTML)

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        async with Client(mcp) as client:
            response = await client.call_tool("fetch_problems")

        assert response.data
