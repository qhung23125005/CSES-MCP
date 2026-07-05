"""
Tests for the fetch_problems tool: parsing logic, tool wrapper, and a
manual live smoke test against the real CSES site.
"""

import functools
import os
from pathlib import Path

import httpx
import pytest

from src.cses_mcp.config.settings import settings
from src.cses_mcp.tools.fetch_problems_tools import (
    _parse_problems, fetch_problems,
    _parse_statement, fetch_problem_statement
)

PROBLEMSET_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_problemset_sample.html"
).read_text(encoding="utf-8")

STATEMENT_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_problem_statement_sample.html"
).read_text(encoding="utf-8")


class TestParseProblems:
    """Tier 1: pure parsing logic, no network involved."""

    def test_parse_problems_categorizes_and_maps_status(self):
        problems = _parse_problems(PROBLEMSET_HTML, None, None)

        # The "General" category is skipped entirely.
        assert all(p["name"] != "Should Be Skipped" for p in problems)
        assert len(problems) == 4

        by_name = {p["name"]: p for p in problems}

        weird = by_name["Weird Algorithm"]
        assert weird["category"] == "Introductory Problems"
        assert weird["status"] == "completed"
        assert weird["link"] == "https://cses.fi/problemset/task/1068"

        missing = by_name["Missing Number"]
        assert missing["status"] == "not accepted"

        repetitions = by_name["Repetitions"]
        assert repetitions["status"] == "not completed"

        distinct = by_name["Distinct Numbers"]
        assert distinct["category"] == "Sorting and Searching"
        assert distinct["status"] == "completed"

    def test_filters_by_category_case_and_whitespace_insensitively(self):
        problems = _parse_problems(PROBLEMSET_HTML, "  sorting AND searching  ", None)

        assert {p["name"] for p in problems} == {"Distinct Numbers"}

    def test_filters_by_status_case_insensitively(self):
        problems = _parse_problems(PROBLEMSET_HTML, None, "NOT Accepted")

        assert {p["name"] for p in problems} == {"Missing Number"}

    def test_filters_by_category_and_status_combined(self):
        problems = _parse_problems(PROBLEMSET_HTML, "Introductory Problems", "completed")

        assert {p["name"] for p in problems} == {"Weird Algorithm"}

    def test_unknown_category_returns_no_problems(self):
        problems = _parse_problems(PROBLEMSET_HTML, "Nonexistent Category", None)

        assert problems == []


class TestFetchProblemsTool:
    """Tier 2: tool wrapper behavior, HTTP mocked so no network is used."""

    @pytest.mark.asyncio
    async def test_uses_configured_session_cookie_and_returns_parsed_problems(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            assert "PHPSESSID=test-cookie-value" in request.headers.get("cookie", "")
            return httpx.Response(200, text=PROBLEMSET_HTML)

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await fetch_problems()

        assert isinstance(result, list)
        assert any(p["name"] == "Weird Algorithm" for p in result)

    @pytest.mark.asyncio
    async def test_forwards_category_and_status_filters(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=PROBLEMSET_HTML)

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await fetch_problems(category="Sorting and Searching", status="completed")

        assert [p["name"] for p in result] == ["Distinct Numbers"]

    @pytest.mark.asyncio
    async def test_returns_error_response_on_http_failure(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="unauthorized")

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await fetch_problems()

        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_returns_auth_error_when_no_cookie_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", None)

        result = await fetch_problems()

        assert result["error"] is True
        assert result["error_code"] == "CSES_NOT_AUTHENTICATED"


class TestFetchProblemsLiveSmoke:
    """
    Tier 3: manual, opt-in smoke test against the real CSES site.

    Skipped unless PHPSESSID is set (via the server's .env). Not run as part
    of the default `make test` since it requires a real, unexpired session
    cookie and hits the live network.
    """

    @pytest.mark.skipif(
        not settings.phpsessid,
        reason="requires a real PHPSESSID configured in .env",
    )
    @pytest.mark.asyncio
    async def test_fetch_problems_against_live_site(self):
        result = await fetch_problems()

        assert isinstance(result, list)
        assert len(result) > 0
        assert {"name", "link", "status", "category"} <= result[0].keys()


class TestParseStatement:
    """Tier 1: pure parsing logic, no network involved."""

    def test_parse_problem_statement(self):
        statement = _parse_statement(STATEMENT_HTML)

        assert statement["Title"] == "Weird Algorithm"
        assert statement["Limit"] == {"time_limit": "1.00 s", "memory_limit": "512 MB"}

        # All 3 <p> tags before the first <h1> must be captured, not just the first.
        description = statement["description"]
        assert "Consider an algorithm" in description
        assert "The algorithm repeats this" in description
        assert "Your task is to simulate" in description

        sections = statement["sections"]
        assert sections["input"] == "The only input line contains an integer n."
        assert sections["output"] == (
            "Print a line that contains all values of n during the algorithm."
        )
        assert sections["constraints"] == "1 \\le n \\le 10^6"
        assert sections["example"] == "Input:\n\n3\n\nOutput:\n\n3 10 5 16 8 4 2 1"

class TestFetchStatementTool:
    """Tier 2: tool wrapper behavior, HTTP mocked so no network is used."""

    @pytest.mark.asyncio
    async def test_fetch_problem_statement_returns_parsed_statement(self, monkeypatch):
        requested_urls = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested_urls.append(str(request.url))
            return httpx.Response(200, text=STATEMENT_HTML)

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        url = "https://cses.fi/problemset/task/1068"
        result = await fetch_problem_statement(url)

        assert requested_urls == [url]
        assert result["Title"] == "Weird Algorithm"
        assert result["Limit"] == {"time_limit": "1.00 s", "memory_limit": "512 MB"}
        assert result["sections"]["constraints"] == "1 \\le n \\le 10^6"

    @pytest.mark.asyncio
    async def test_returns_error_response_on_http_failure(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="not found")

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await fetch_problem_statement("https://cses.fi/problemset/task/999999")

        assert result["error"] is True
        assert result["tool_args"] == {"url": "https://cses.fi/problemset/task/999999"}


class TestFetchStatementLiveSmoke:
    """
    Tier 3: manual, opt-in smoke test against the real CSES site.

    Skipped unless RUN_LIVE_TESTS=1 is set. Not run as part of the default
    `make test` since it hits the live network and depends on cses.fi being
    reachable. No session cookie is needed since problem statements are
    public data.
    """

    @pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="set RUN_LIVE_TESTS=1 to run this test against the real CSES site",
    )
    @pytest.mark.asyncio
    async def test_fetch_problem_statement_against_live_site(self):
        result = await fetch_problem_statement("https://cses.fi/problemset/task/1068")

        assert result["Title"] == "Weird Algorithm"
        assert result["Limit"]["time_limit"]
        assert result["Limit"]["memory_limit"]
        assert result["description"]
        assert result["sections"]["input"]
        assert result["sections"]["output"]
        assert result["sections"]["constraints"]
        assert result["sections"]["example"]
