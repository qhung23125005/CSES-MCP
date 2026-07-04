"""
Pytest configuration and fixtures for CSES MCP server tests.
"""

import pytest
from dotenv import load_dotenv

from src.cses_mcp.config.settings import Settings

load_dotenv()


@pytest.fixture
def test_settings() -> Settings:
    """Provide test-specific settings."""
    return Settings(
        server_name="cses-mcp-test",
        log_level="DEBUG",
        enable_debug=True,
    )
