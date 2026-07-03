"""
Validation utilities for the CSES MCP server.
"""

import re
from typing import Any


class MCPValidationError(Exception):
    """Custom exception for MCP validation errors."""

    pass


def sanitize_input(value: Any, max_length: int = 1000) -> str:
    """
    Sanitize user input for security.

    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        MCPValidationError: If input is invalid
    """
    if value is None:
        return ""

    str_value = str(value)

    if len(str_value) > max_length:
        raise MCPValidationError(f"Input exceeds maximum length of {max_length}")

    sanitized = re.sub(r'[<>"\']', "", str_value)

    return sanitized.strip()
