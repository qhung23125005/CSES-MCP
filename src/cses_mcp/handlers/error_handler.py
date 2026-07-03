"""
Error handling utilities for the CSES MCP server.
"""

import traceback
from datetime import datetime
from typing import Any

from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger("cses_mcp.handlers.error")


class MCPError(Exception):
    """Base exception class for MCP-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class ToolError(MCPError):
    """Exception for tool-related errors."""

    pass


class CSESAuthError(MCPError):
    """Exception raised when the CSES session is missing or expired."""

    pass


class CSESScrapeError(MCPError):
    """Exception raised when CSES page structure doesn't match what the scraper expects."""

    pass


class ErrorHandler:
    """Centralized error handling for the MCP server."""

    def __init__(self) -> None:
        self.logger = setup_logger("cses_mcp.error_handler")
        self.error_counts: dict[str, int] = {}

    def handle_tool_error(
        self, tool_name: str, error: Exception, args: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Handle an error raised during tool execution and return a standardized
        error response instead of letting a raw traceback reach the client.

        Args:
            tool_name: Name of the tool where the error occurred
            error: The exception that occurred
            args: Arguments passed to the tool

        Returns:
            Standardized error response dictionary
        """
        if isinstance(error, MCPError):
            error_code = error.error_code
            error_message = error.message
            error_details = error.details
        else:
            error_code = type(error).__name__
            error_message = str(error)
            error_details = {}

        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1

        error_response: dict[str, Any] = {
            "error": True,
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "tool_args": args,
            "details": error_details,
        }

        if settings.enable_debug:
            error_response["traceback"] = traceback.format_exc()

        log_message = f"Error in tool:{tool_name}: {error_message}"
        if isinstance(error, MCPError):
            self.logger.warning(log_message)
        else:
            self.logger.error(log_message, exc_info=True)

        return error_response


# Global error handler instance
error_handler = ErrorHandler()
