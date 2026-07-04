"""
Configuration settings for the CSES MCP server.
"""

from pathlib import Path

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

# Anchored to the project root rather than left relative, since relative
# paths are resolved against the process's current working directory —
# which callers that spawn this server (e.g. Claude Desktop's "uv run
# --project ..." config) don't set to the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    server_name: str = Field(default="cses-mcp", description="Name of the MCP server")
    server_version: str = Field(default="0.1.0", description="Version of the server")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    log_file: str | None = Field(default=None, description="Log file path")

    # Feature Flags
    enable_debug: bool = Field(default=False, description="Enable debug mode")

    # CSES Configuration
    cses_base_url: str = Field(default="https://cses.fi", description="Base URL for CSES")
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    phpsessid: str | None = Field(
        default=None, description="CSES session cookie (PHPSESSID) used for authenticated requests"
    )


# Global settings instance
settings = Settings()
