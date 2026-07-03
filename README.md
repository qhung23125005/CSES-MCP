# CSES MCP Server

An MCP (Model Context Protocol) server that lets an AI assistant act on your
behalf on [CSES](https://cses.fi) (Code Submission Evaluation System):
browsing problems, checking submission status/history, retrieving past
submitted code, and submitting new solutions. See
[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for the full scope.

CSES has no public API — all data access is via scraping authenticated HTML
pages and posting to existing web forms using your own session.

## Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Install dependencies

```bash
uv sync --all-extras
cp .env.example .env
```

### 2. Run the server

```bash
make run              # STDIO transport (default)
make run-debug        # STDIO with debug logging
make run-sse          # SSE transport on port 8000
make run-inspector     # Run with the MCP Inspector
```

### 3. Test

```bash
make test             # Run tests
make test-cov         # Run tests with coverage
make lint             # Ruff lint
make format           # Ruff format/fix
```

## Using with Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "cses-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "cses_mcp.main"],
      "cwd": "/path/to/CSES-MCP"
    }
  }
}
```

## Project Structure

```
src/cses_mcp/
├── __init__.py
├── main.py              # CLI entry point
├── server.py            # Core server implementation
├── client.py            # Ad-hoc script for exercising the server locally
├── config/
│   └── settings.py      # Configuration management (pydantic-settings)
├── tools/                # MCP tools
│   └── fetch_problems_tools.py
├── resources/            # MCP resources (scaffolded, empty)
├── prompts/               # MCP prompts (scaffolded, empty)
├── handlers/
│   └── error_handler.py # Centralized tool error handling
└── utils/
    ├── logger.py
    └── validation.py
```

## Adding Tools, Resources, and Prompts

1. Create a new file under `src/cses_mcp/tools/` (or `resources/`, `prompts/`)
   using `from ..server import mcp` and the relevant `@mcp.tool` /
   `@mcp.resource` / `@mcp.prompt` decorator.
2. Register the module by importing it in that package's `__init__.py`.

## Configuration

Copy `.env.example` to `.env` and customize. See
[src/cses_mcp/config/settings.py](src/cses_mcp/config/settings.py) for all
available settings (server name, log level/file, debug mode, CSES base URL,
request timeout).

## Security

- Session cookies/credentials must never be logged, printed in tool output,
  or transmitted anywhere except cses.fi.
- Requests to CSES should be sequential and rate-limited, not parallelized.

See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for full non-functional
requirements.
