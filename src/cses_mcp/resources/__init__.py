"""
Resources module for the CSES MCP server.

Import resource modules here to register them with the MCP server, e.g.:

    from . import problem_resources
"""

from . import cses_categories

__all__: list[str] = ["cses_categories"]
