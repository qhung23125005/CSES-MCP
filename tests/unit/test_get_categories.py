"""
Tests for the fetch_categories resource: HTTP mocked against the local
fixture so no real network call is made and the assertions don't depend
on CSES's live site content, plus an opt-in smoke test against the real
CSES server.
"""

import functools
import os
from pathlib import Path

import httpx
import pytest

from src.cses_mcp.handlers.error_handler import CSESScrapeError
from src.cses_mcp.resources.cses_categories import fetch_categories

FIXTURE_HTML = (
    Path(__file__).parent.parent / "fixtures" / "cses_problemset_sample.html"
).read_text(encoding="utf-8")


def _mock_client(html: str) -> functools.partial:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    return functools.partial(httpx.AsyncClient, transport=httpx.MockTransport(handler))


class TestFetchCategories:
    @pytest.mark.asyncio
    async def test_returns_categories_excluding_general(self, monkeypatch):
        monkeypatch.setattr(httpx, "AsyncClient", _mock_client(FIXTURE_HTML))

        categories = await fetch_categories()

        assert categories == ["Introductory Problems", "Sorting and Searching"]

    @pytest.mark.asyncio
    async def test_raises_scrape_error_when_no_categories_found(self, monkeypatch):
        monkeypatch.setattr(httpx, "AsyncClient", _mock_client("<html><body></body></html>"))

        with pytest.raises(CSESScrapeError):
            await fetch_categories()


class TestFetchCategoriesLiveSmoke:
    """
    Opt-in smoke test against the real CSES site.

    Skipped unless RUN_LIVE_TESTS=1 is set. Not run as part of the default
    `make test` since it hits the live network and depends on cses.fi being
    reachable. No session cookie is needed since categories are public data.
    """

    @pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="set RUN_LIVE_TESTS=1 to run this test against the real CSES site",
    )
    @pytest.mark.asyncio
    async def test_fetch_categories_against_live_site(self):
        categories = await fetch_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert all(isinstance(c, str) for c in categories)
        assert "General" not in categories
