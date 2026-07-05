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


def _parse_problems(
    html: str, filter_category: str | None, filter_status: str | None
) -> list[dict]:
    """Pure parsing step, kept separate from the network call so it's unit-testable."""
    soup = BeautifulSoup(html, "lxml")

    filter_category_norm = filter_category.strip().lower() if filter_category else None
    filter_status_norm = filter_status.strip().lower() if filter_status else None

    problems = []
    for h2 in soup.find_all("h2"):
        category = h2.get_text().strip()

        # The first h2 is General -> Skip it
        if category == "General":
            continue

        # If category is passed as an argument, check (case/whitespace-insensitive)
        if filter_category_norm and category.lower() != filter_category_norm:
            continue

        # Next to the h2 is the list of problems --> Get the next one
        ul = h2.find_next_sibling("ul", class_="task-list")
        if ul is None:
            continue

        # Loop through all the problems
        for li in ul.find_all("li", class_="task"):
            a = li.find("a")
            if a is None:
                continue

            status = _parse_status(li)
            if filter_status_norm and status != filter_status_norm:
                continue

            problems.append({
                "name": a.get_text(),
                "link": settings.cses_base_url + a["href"],
                "status": status,
                "category": category
            })

    return problems


@mcp.tool(
    tags={"fetch_data", "fetch_problems"},
    meta={"version": "0.0.1"}
)
async def fetch_problems(category: str | None = None, status: str | None = None) -> list[dict]:
    """
    Fetch every problem listed on the CSES problem set page, grouped by category.

    This scrapes https://cses.fi/problemset/ (or the configured CSES_BASE_URL) and
    returns each problem's name, link, category, and the current user's completion
    status for it. Use this tool when the user wants to browse/list CSES problems,
    find problems in a specific category (e.g. "Sorting and Searching", "Graph
    Algorithms"), or check which problems they have/haven't solved yet.

    Args:
        category: Optional category name to filter by, e.g. "Sorting and Searching"
            or "Graph Algorithms". Matching is case-insensitive and ignores
            surrounding whitespace. If omitted, problems from all categories are
            returned.
        status: Optional completion status to filter by. Must be one of
            "completed", "not accepted", or "not completed" (case-insensitive).
            If omitted, problems with any status are returned.

    Authentication:
        Requires a valid CSES session cookie (PHPSESSID) configured on the server
        via the .env file. This is the same cookie your browser sends when logged
        into cses.fi, and it determines whose solve status is reported. If it is
        missing or has expired, this tool returns an error dict instead of raising.

    Returns:
        On success, a list of dicts, one per problem, each shaped like:
            {
                "name": str,      # Problem title, e.g. "Weird Algorithm"
                "link": str,      # Absolute URL to the problem page
                "status": str,    # One of "completed", "not accepted", "not completed"
                "category": str,  # Section heading on the problem set page,
                                  # e.g. "Introductory Problems", "Sorting and Searching"
            }
        The "General" section on the page (site info, not real problems) is
        excluded. Problem order follows the page's natural order.

        On failure (e.g. missing/expired session cookie, network error, or the
        CSES page structure changing), returns a single error dict from
        error_handler.handle_tool_error with keys "error", "error_code",
        "message", "timestamp", "tool_name", "tool_args", and "details" — check
        for `"error": True` before treating the result as a problem list.
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

        return _parse_problems(response.text, category, status)
    except Exception as e:
        return error_handler.handle_tool_error("fetch_problems", e, {})
    
@mcp.tool(
    tags={"fetch_data", "fetch_statement"},
    meta={"version": "0.0.1"}
)
async def fetch_problem_statement(url: str) -> dict:
    pass
