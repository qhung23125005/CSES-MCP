"""
Tests for the fetch_problems tool: parsing logic, tool wrapper, and a
manual live smoke test against the real CSES site.
"""

import functools
from pathlib import Path

import httpx
import pytest

from src.cses_mcp.config.settings import settings
from src.cses_mcp.tools.fetch_problems_tools import _parse_problems, fetch_problems

FIXTURE_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_problemset_sample.html"
).read_text(encoding="utf-8")


class TestParseProblems:
    """Tier 1: pure parsing logic, no network involved."""

    def test_parse_problems_categorizes_and_maps_status(self):
        problems = _parse_problems(FIXTURE_HTML, None, None)

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
        problems = _parse_problems(FIXTURE_HTML, "  sorting AND searching  ", None)

        assert {p["name"] for p in problems} == {"Distinct Numbers"}

    def test_filters_by_status_case_insensitively(self):
        problems = _parse_problems(FIXTURE_HTML, None, "NOT Accepted")

        assert {p["name"] for p in problems} == {"Missing Number"}

    def test_filters_by_category_and_status_combined(self):
        problems = _parse_problems(FIXTURE_HTML, "Introductory Problems", "completed")

        assert {p["name"] for p in problems} == {"Weird Algorithm"}

    def test_unknown_category_returns_no_problems(self):
        problems = _parse_problems(FIXTURE_HTML, "Nonexistent Category", None)

        assert problems == []


class TestFetchProblemsTool:
    """Tier 2: tool wrapper behavior, HTTP mocked so no network is used."""

    @pytest.mark.asyncio
    async def test_uses_configured_session_cookie_and_returns_parsed_problems(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            assert "PHPSESSID=test-cookie-value" in request.headers.get("cookie", "")
            return httpx.Response(200, text=FIXTURE_HTML)

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
            return httpx.Response(200, text=FIXTURE_HTML)

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
