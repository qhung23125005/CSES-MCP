"""
Tests for the submit_code and fetch_submission tools, with HTTP mocked so no
real submission ever hits the live CSES site.
"""

import functools
import os
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

from src.cses_mcp.config.settings import settings
from src.cses_mcp.tools.submission_tools import (
    _parse_hidden_fields,
    _parse_submission,
    fetch_submission,
    submit_code,
)

SUBMIT_FORM_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_submit_form_sample.html"
).read_text(encoding="utf-8")

SUBMISSION_RESULT_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_submission_result_sample.html"
).read_text(encoding="utf-8")


class TestParseHiddenFields:
    """Tier 1: pure parsing logic, no network involved."""

    def test_extracts_all_hidden_inputs_from_the_form(self):
        soup = BeautifulSoup(SUBMIT_FORM_HTML, "lxml")

        hidden_fields = _parse_hidden_fields(soup)

        assert hidden_fields == {
            "csrf_token": "fake-csrf-token-abc123",
            "task": "1068",
            "type": "course",
            "target": "problemset",
        }


class TestSubmitCodeTool:
    """Tier 2: tool wrapper behavior, HTTP mocked so no network is used."""

    @pytest.mark.asyncio
    async def test_returns_auth_error_when_no_cookie_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", None)

        result = await submit_code("1068", "solution.py", "print(1)")

        assert result["error"] is True
        assert result["error_code"] == "CSES_NOT_AUTHENTICATED"

    @pytest.mark.asyncio
    async def test_returns_error_for_unsupported_extension(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        result = await submit_code("1068", "solution.txt", "print(1)")

        assert result["error"] is True
        assert result["error_code"] == "UNSUPPORTED_LANGUAGE"

    @pytest.mark.asyncio
    async def test_submits_code_and_returns_submission_id(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, text=SUBMIT_FORM_HTML)

            # The form's action is /course/send.php, a different path than the
            # GET submit page — regression check for a bug where the code
            # POSTed back to the submit page URL instead of the form's action.
            assert str(request.url) == "https://cses.fi/course/send.php"
            assert "PHPSESSID=test-cookie-value" in request.headers.get("cookie", "")
            body = request.content
            assert b"fake-csrf-token-abc123" in body
            assert b"Python3" in body
            assert b"print(1)" in body
            return httpx.Response(302, headers={"location": "/problemset/result/17833261/"})

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await submit_code("1068", "solution.py", "print(1)")

        assert result == {
            "task_id": "1068",
            "submission_id": "17833261",
            "redirect": "/problemset/result/17833261/",
        }

    @pytest.mark.asyncio
    async def test_returns_error_when_cses_does_not_redirect(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, text=SUBMIT_FORM_HTML)
            return httpx.Response(200, text="submission rejected")

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await submit_code("1068", "solution.py", "print(1)")

        assert result["error"] is True
        assert result["error_code"] == "SUBMISSION_NOT_ACCEPTED"


class TestParseSubmission:
    """Tier 1: pure parsing logic, no network involved."""

    def test_extracts_summary_tests_and_code(self):
        submission = _parse_submission(SUBMISSION_RESULT_HTML)

        assert submission["task"] == {
            "name": "Weird Algorithm",
            "link": "https://cses.fi/problemset/task/1068/",
        }
        assert submission["sender"] == "dogedicode"
        assert submission["submission_time"] == "2026-07-06 11:38:38 +0300"
        assert submission["language"] == "Python3 (PyPy3)"
        assert submission["status"] == "READY"
        assert submission["result"] == "ACCEPTED"

        assert submission["tests"] == [
            {"test": "#1", "verdict": "ACCEPTED", "time": "0.04 s"},
            {"test": "#2", "verdict": "ACCEPTED", "time": "0.04 s"},
        ]

        assert submission["code"] == (
            "n = int(input())\n"
            "result = [n]\n"
            "while n != 1:\n"
            "    if n % 2 == 0:\n"
            "        n //= 2\n"
            "    else:\n"
            "        n = 3 * n + 1\n"
            "    result.append(n)\n"
            "print(*result)"
        )


class TestFetchSubmissionTool:
    """Tier 2: tool wrapper behavior, HTTP mocked so no network is used."""

    @pytest.mark.asyncio
    async def test_returns_auth_error_when_no_cookie_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", None)

        result = await fetch_submission("17833364")

        assert result["error"] is True
        assert result["error_code"] == "CSES_NOT_AUTHENTICATED"

    @pytest.mark.asyncio
    async def test_fetches_and_parses_submission(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://cses.fi/problemset/result/17833364/"
            assert "PHPSESSID=test-cookie-value" in request.headers.get("cookie", "")
            return httpx.Response(200, text=SUBMISSION_RESULT_HTML)

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await fetch_submission("17833364")

        assert result["result"] == "ACCEPTED"
        assert result["task"]["name"] == "Weird Algorithm"
        assert len(result["tests"]) == 2

    @pytest.mark.asyncio
    async def test_returns_scrape_error_when_summary_table_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "phpsessid", "test-cookie-value")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html><body>not found</body></html>")

        mock_transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=mock_transport)
        )

        result = await fetch_submission("nonexistent")

        assert result["error"] is True
        assert result["error_code"] == "SUBMISSION_NOT_FOUND"


class TestFetchSubmissionLiveSmoke:
    """
    Tier 3: manual, opt-in smoke test against the real CSES site.

    Skipped unless RUN_LIVE_TESTS=1 is set AND a real PHPSESSID is configured
    (via the server's .env). Not run as part of the default `make test` since
    it requires a real, unexpired session cookie and hits the live network.
    """

    @pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1" or not settings.phpsessid,
        reason="set RUN_LIVE_TESTS=1 and a real PHPSESSID in .env to run this test",
    )
    @pytest.mark.asyncio
    async def test_fetch_submission_against_live_site(self):
        result = await fetch_submission("17833364")

        assert result["result"] == "ACCEPTED"
        assert result["task"]["name"] == "Weird Algorithm"
