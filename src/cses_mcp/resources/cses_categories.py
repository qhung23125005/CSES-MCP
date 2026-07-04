from ..config.settings import settings
from ..handlers.error_handler import CSESScrapeError
from ..server import mcp
from ..utils.logger import setup_logger

from bs4 import BeautifulSoup
import httpx

logger = setup_logger("cses_mcp.resources.cses_categories")

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


@mcp.resource(
    uri="data://categories",
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
    to pass as the `category` filter on the `fetch_problems` tool.

    Returns:
        A list of category name strings, e.g.:
            ["Introductory Problems", "Sorting and Searching", "Dynamic Programming", ...]

    Raises:
        CSESScrapeError: if no categories are found, meaning the CSES page
            structure no longer matches what this scraper expects.
        httpx.HTTPStatusError: if the request to CSES fails (e.g. site down).
    """
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

