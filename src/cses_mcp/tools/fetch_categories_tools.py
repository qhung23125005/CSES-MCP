from ..config.settings import settings
from ..handlers.error_handler import CSESScrapeError, error_handler
from ..server import mcp
from ..utils.logger import setup_logger

from bs4 import BeautifulSoup
import httpx

logger = setup_logger("cses_mcp.tools.fetch_categories")

BASE_URL = f"{settings.cses_base_url}/problemset/"

def _parse_categories(html: str) -> list[str]:
    """Pure parsing step, kept separate from the network call so it's unit-testable."""
    soup = BeautifulSoup(html, "lxml")

    categories = []
    for h2 in soup.find_all("h2"):
        category = h2.get_text().strip()

        # The first h2 is General -> Skip it
        if category == "General":
            continue

        categories.append(category)

    return categories


@mcp.tool(
    tags={"fetch_data", "fetch_categories"},
    meta={"version": "0.0.1"}
)
async def fetch_categories() -> list[str]:
    """
    List every problem category name on the CSES problem set page.

    This scrapes https://cses.fi/problemset/ (or the configured CSES_BASE_URL) and
    returns the section headings (e.g. "Introductory Problems", "Sorting and
    Searching", "Graph Algorithms") in page order, excluding the "General"
    section (site info, not a problem category). This is public data — no
    session cookie is required. Use this to look up the exact category string
    to pass as the `category` filter on the `fetch_problems` tool, since that
    filter requires an exact (case/whitespace-insensitive) match.

    Returns:
        On success, a list of category name strings, e.g.:
            ["Introductory Problems", "Sorting and Searching", "Dynamic Programming", ...]

        On failure (e.g. network error, or the CSES page structure changing),
        returns a single error dict from error_handler.handle_tool_error with
        keys "error", "error_code", "message", "timestamp", "tool_name",
        "tool_args", and "details" — check for `"error": True` before treating
        the result as a category list.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(BASE_URL)
            response.raise_for_status()

        categories = _parse_categories(response.text)
        if not categories:
            raise CSESScrapeError(
                "No categories found on the CSES problem set page; the page "
                "structure may have changed.",
                error_code="CSES_SCRAPE_STRUCTURE_CHANGED",
            )

        return categories
    except Exception as e:
        return error_handler.handle_tool_error("fetch_categories", e, {})
