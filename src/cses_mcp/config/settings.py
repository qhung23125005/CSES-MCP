"""
Configuration settings for the CSES MCP server.
"""

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
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
