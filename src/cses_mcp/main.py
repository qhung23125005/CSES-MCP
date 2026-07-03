"""
CLI entry point for the CSES MCP server.
"""

import argparse
import sys

from .config.settings import settings
from .server import main as server_main
from .utils.logger import setup_logger

logger = setup_logger("cses_mcp.main")


def main() -> None:
    """Parse CLI args, apply setting overrides, and run the server."""
    parser = argparse.ArgumentParser(description="CSES MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set log level",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport")

    args = parser.parse_args()

    if args.debug:
        settings.enable_debug = True
        settings.log_level = "DEBUG"

    if args.log_level:
        settings.log_level = args.log_level

    try:
        if args.transport == "sse":
            from .server import mcp

            mcp.run(transport="sse", port=args.port)
        else:
            server_main()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
