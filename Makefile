# CSES MCP Server Makefile

.PHONY: help install install-dev test test-cov lint format clean run run-debug run-sse run-inspector build

help:
	@echo "Available commands:"
	@echo "  install        - Install production dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  test           - Run tests"
	@echo "  test-cov       - Run tests with coverage"
	@echo "  lint           - Run linting (ruff)"
	@echo "  format         - Format code (ruff)"
	@echo "  clean          - Clean build artifacts"
	@echo "  run            - Run the MCP server (STDIO)"
	@echo "  run-debug      - Run the MCP server in debug mode (STDIO)"
	@echo "  run-sse        - Run the MCP server with SSE transport"
	@echo "  run-inspector  - Run the MCP server with MCP Inspector"
	@echo "  build          - Build the package"

install:
	uv sync --no-dev

install-dev:
	uv sync --all-extras

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src --cov-report=html --cov-report=term

lint:
	uv run ruff check src tests

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	uv run python -m cses_mcp.main

run-debug:
	uv run python -m cses_mcp.main --debug

run-sse:
	uv run python -m cses_mcp.main --transport sse --port 8000

run-inspector:
	uv run fastmcp dev inspector -m cses_mcp.server

build:
	uv build
