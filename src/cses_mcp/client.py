import asyncio

from fastmcp import Client

from .server import mcp


async def main():
    # In-process connection to the mcp instance (no subprocess spawned,
    # so this doesn't hit the relative-import issues a standalone script run would).
    async with Client(mcp) as client:
        # List tools to verify registration
        tools = await client.list_tools()
        print(f"Registered tools: {[t.name for t in tools]}")

        # Call the tool (session cookie comes from the server's own .env)
        response = await client.call_tool("fetch_problems")
        print(f"Tool response: {response.data}")

if __name__ == "__main__":
    asyncio.run(main())
