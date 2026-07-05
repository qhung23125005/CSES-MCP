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

def _parse_limits(soup: BeautifulSoup) -> dict[str, str]:
    """
    Extract the time/memory limit box: <ul class="task-constraints">
    <li><b>Time limit:</b> 1.00 s</li><li><b>Memory limit:</b> 512 MB</li></ul>
    Returns e.g. {"time_limit": "1.00 s", "memory_limit": "512 MB"}.
    """
    limits: dict[str, str] = {}
    ul = soup.find("ul", class_="task-constraints")
    if ul is None:
        return limits

    for li in ul.find_all("li"):
        b_tag = li.find("b")
        if b_tag is None:
            continue

        label = b_tag.text.strip().rstrip(":").lower().replace(" ", "_")
        value = (b_tag.next_sibling or "").strip()
        limits[label] = value

    return limits


def _parse_description(soup: BeautifulSoup) -> str:
    """
    Extract the narrative problem description: every top-level child of
    <div class="md"> before the first <h1> (which marks the start of the
    "Input" section). Some problems have multiple <p> tags here, not just one.
    """
    md = soup.find("div", class_="md")
    if md is None:
        return ""

    paragraphs = []
    for child in md.find_all(recursive=False):
        if child.name == "h1":
            break

        paragraphs.append(child.get_text().strip())

    return "\n\n".join(p for p in paragraphs if p)


def _parse_sections(soup: BeautifulSoup) -> dict[str, str]:
    """
    Extract each <h1>-delimited section inside <div class="md"> that comes
    after the description, e.g. "Input", "Output", "Constraints", "Example".
    Returns {section_name_lowercased: section_text}, so e.g.
    {"input": "...", "output": "...", "constraints": "1 \\le n \\le 10^6", "example": "..."}.
    """
    md = soup.find("div", class_="md")
    if md is None:
        return {}

    sections: dict[str, str] = {}
    current_name: str | None = None
    current_parts: list[str] = []

    for child in md.find_all(recursive=False):
        if child.name == "h1":
            if current_name is not None:
                sections[current_name] = "\n\n".join(p for p in current_parts if p)
            current_name = child.get_text().strip().lower()
            current_parts = []
        elif current_name is not None:
            current_parts.append(child.get_text().strip())

    if current_name is not None:
        sections[current_name] = "\n\n".join(p for p in current_parts if p)

    return sections


def _parse_statement(html: str) -> dict:
    """Pure parsing step, kept separate from the network call so it's unit-testable."""
    soup = BeautifulSoup(html, "lxml")

    limits = _parse_limits(soup)
    sections = _parse_sections(soup)

    return {
        "Title": soup.find("h1").get_text().strip(),
        "Limit": limits,
        "description": _parse_description(soup),
        "sections": sections
    }


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
    """
    Fetch a single CSES problem's statement, given its problem page URL.

    This scrapes a problem page (e.g. one of the links returned by
    `fetch_problems`, such as https://cses.fi/problemset/task/1068) and returns
    its title, time/memory limits, narrative description, and the Input,
    Output, Constraints, and Example sections. This is public data — no
    session cookie is required. Math notation in the description/sections is
    returned as its raw LaTeX source (e.g. "n \\le 10^6"), not rendered.

    Args:
        url: Absolute URL to a CSES problem page, e.g.
            "https://cses.fi/problemset/task/1068".

    Returns:
        On success, a dict shaped like:
            {
                "title": str,          # e.g. "Weird Algorithm"
                "time_limit": str,     # e.g. "1.00 s"
                "memory_limit": str,   # e.g. "512 MB"
                "description": str,    # narrative problem statement
                "input": str,          # description of the input format
                "output": str,         # description of the output format
                "constraints": str,    # e.g. "1 \\le n \\le 10^6"
                "example": str,        # sample input/output as shown on the page
            }
        Any of the section values may be None if that section doesn't appear
        on the page (e.g. interactive problems format Input/Output differently).

        On failure (e.g. invalid URL, network error, or the CSES page
        structure changing), returns a single error dict from
        error_handler.handle_tool_error with keys "error", "error_code",
        "message", "timestamp", "tool_name", "tool_args", and "details" — check
        for `"error": True` before treating the result as a statement.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

        return _parse_statement(response.text)
    except Exception as e:
        return error_handler.handle_tool_error("fetch_problem_statement", e, {"url": url})
