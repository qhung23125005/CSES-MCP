"""
Main MCP server implementation using FastMCP v2.
"""

from fastmcp import FastMCP

from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger("cses_mcp.server")

mcp = FastMCP(
    name=settings.server_name,
    version=settings.server_version,
    instructions=(
        "This MCP server provides tools to interact with the CSES (Code Submission "
        "Evaluation System) platform. It allows users to browse problems, check "
        "submission status/history, retrieve past submitted code, and submit new "
        "solutions using the user's own CSES session."
    ),
)

# Import all components to register them with the mcp instance
from .prompts import *  # noqa: E402,F403  registers all prompts
from .resources import *  # noqa: E402,F403  registers all resources
from .tools import *  # noqa: E402,F403  registers all tools

logger.info(f"Initialized FastMCP server: {settings.server_name}")


def main() -> None:
    """Run the MCP server."""
    try:
        logger.info("Starting MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        raise
    finally:
        logger.info("Server shutdown complete")
