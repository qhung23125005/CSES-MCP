from ..config.settings import settings
from ..handlers.error_handler import CSESAuthError, CSESScrapeError, error_handler
from ..server import mcp
from ..utils.logger import setup_logger

from bs4 import BeautifulSoup
import httpx
from pathlib import Path

logger = setup_logger("cses_mcp.tools.submission_tools")

BASE_URL = f"{settings.cses_base_url}/problemset/submit"
EXTENSION_TO_LANG = {
    ".asm": "Assembly",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".hs": "Haskell",
    ".java": "Java",
    ".js": "Node.js",
    ".pas": "Pascal",
    ".py": "Python3",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".scala": "Scala",
}



def _parse_hidden_fields(soup: BeautifulSoup) -> dict: 
    hiddens = {}
    form = soup.find("form")
    for hidden in form.find_all("input", type="hidden"):
        label = hidden["name"]
        value = hidden["value"]
        hiddens[label] = value

    return hiddens

@mcp.tool(
    tags={"submission_tool", "submit"},
    meta={"version": "0.0.1"}
)
async def submit_code(task_id: str, filename: str, code: str) -> dict:
    """
    Submit a solution to a CSES problem for judging.

    Scrapes the task's submit page for a fresh CSRF token and hidden form
    fields, then uploads the given source code (in-memory, no filesystem
    access) to CSES for judging. The language is inferred from `filename`'s
    extension.

    Args:
        task_id: The CSES task id, e.g. "1068" (from a problem's URL
            .../problemset/task/1068).
        filename: A filename for the source, used only to infer the
            language, e.g. "solution.py". Supported extensions: .asm, .c,
            .cpp/.cc, .hs, .java, .js, .pas, .py, .rb, .rs, .scala.
        code: The full source code to submit, as a string.

    Returns:
        On success, {"task_id": str, "submission_id": str | None,
        "redirect": str | None} — submission_id is parsed from the
        post-submit redirect and is what `get_submission_result` (once
        implemented) would poll.

        On failure (not authenticated, unsupported extension, network
        error, or CSES not redirecting as expected), returns a single error
        dict from error_handler.handle_tool_error with keys "error",
        "error_code", "message", "timestamp", "tool_name", "tool_args", and
        "details" — check for `"error": True` before treating the result as
        a successful submission.
    """
    try:
        if not settings.phpsessid:
            raise CSESAuthError(
                "No CSES session cookie configured. Set PHPSESSID in the server's .env.",
                error_code="CSES_NOT_AUTHENTICATED",
            )

        extension = Path(filename).suffix
        if extension not in EXTENSION_TO_LANG:
            raise CSESScrapeError(
                f"Unsupported file extension '{extension}' for filename '{filename}'.",
                error_code="UNSUPPORTED_LANGUAGE",
            )
        lang = EXTENSION_TO_LANG[extension]

        cookies = {"PHPSESSID": settings.phpsessid}
        async with httpx.AsyncClient(cookies=cookies, timeout=settings.request_timeout) as client:
            response = await client.get(BASE_URL + f"/{task_id}")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            form = soup.find("form")
            data = _parse_hidden_fields(soup)
            data["lang"] = lang

            action = form["action"]
            submit_url = (
                settings.cses_base_url + action if action.startswith("/") else action
            )

            response = await client.post(
                submit_url,
                data=data,
                files={"file": (filename, code.encode())},
                follow_redirects=False,
            )

        if not (300 <= response.status_code < 400) or "location" not in response.headers:
            raise CSESScrapeError(
                f"CSES did not redirect after submission (status {response.status_code}); "
                "the submission may have been rejected.",
                error_code="SUBMISSION_NOT_ACCEPTED",
            )

        location = response.headers["location"]
        submission_id = location.rstrip("/").rsplit("/", 1)[-1] or None

        return {"task_id": task_id, "submission_id": submission_id, "redirect": location}
    except Exception as e:
        return error_handler.handle_tool_error("submit_code", e, {"task_id": task_id})
    
# @mcp.tool(
#     tags={"submission_tool", "fetch_submission"},
#     meta={"version": "0.0.1"}
# )
# async def fetch_submission(submission_id: str):
