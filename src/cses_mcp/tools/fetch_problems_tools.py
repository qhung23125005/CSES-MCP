from ..config.settings import settings
from ..handlers.error_handler import CSESAuthError, error_handler
from ..server import mcp
from ..utils.logger import setup_logger

from bs4 import BeautifulSoup
import httpx

logger = setup_logger("cses_mcp.tools.fetch_problems")

BASE_URL = f"{settings.cses_base_url}/problemset/"


def _parse_status(li) -> str:
    """Map a task's <span class="task-score icon ..."> to a status label."""
    score = li.find("span", class_="task-score")
    classes = score.get("class", []) if score else []
    if "full" in classes:
        return "completed"
    if "zero" in classes:
        return "not accepted"
    return "not completed"


def _parse_problems(html: str) -> list[dict]:
    """Pure parsing step, kept separate from the network call so it's unit-testable."""
    soup = BeautifulSoup(html, "lxml")

    problems = []
    for h2 in soup.find_all("h2"):
        # The first h2 is General -> Skip it
        if h2.get_text() == "General":
            continue

        # Next to the h2 is the list of problems --> Get the next one
        ul = h2.find_next_sibling("ul", class_="task-list")
        if ul is None:
            continue
        category = h2.get_text()

        # Loop through all the problems
        for li in ul.find_all("li", class_="task"):
            a = li.find("a")
            if a is None:
                continue
            problems.append({
                "name": a.get_text(),
                "link": settings.cses_base_url + a["href"],
                "status": _parse_status(li),
                "category": category
            })

    return problems


@mcp.tool
async def fetch_problems() -> list[dict]:
    """
    Fetches the list of available CSES problems.
    Uses the server-configured CSES session cookie (PHPSESSID) for authentication.
    """
    try:
        if not settings.phpsessid:
            raise CSESAuthError(
                "No CSES session cookie configured. Set PHPSESSID in the server's .env.",
                error_code="CSES_NOT_AUTHENTICATED",
            )

        cookies = {"PHPSESSID": settings.phpsessid}
        async with httpx.AsyncClient(cookies=cookies, timeout=settings.request_timeout) as client:
            response = await client.get(BASE_URL)
            response.raise_for_status()

        return _parse_problems(response.text)
    except Exception as e:
        return error_handler.handle_tool_error("fetch_problems", e, {})