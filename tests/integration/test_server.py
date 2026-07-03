"""
Integration tests for the CSES MCP server.
"""

import pytest
from fastmcp import Client

from src.cses_mcp.server import mcp


class TestServerIntegration:
    """Integration tests exercising the running MCP server in-process."""

    @pytest.mark.asyncio
    async def test_tools_are_registered(self):
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]

        assert "fetch_problems" in tool_names

    @pytest.mark.asyncio
    async def test_fetch_problems_tool(self):
        async with Client(mcp) as client:
            response = await client.call_tool("fetch_problems")

        assert response.data
