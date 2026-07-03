from ..handlers.error_handler import error_handler
from ..server import mcp
from ..utils.logger import setup_logger

logger = setup_logger("cses_mcp.tools.fetch_problems")


@mcp.tool
async def fetch_problems() -> list[str]:
    """
    Fetches the list of available CSES problems.
    Requires a valid session cookie for authentication.
    """
    try:
        # 1. Add your HTTP request logic here
        # 2. Return the data as a list or dictionary
        result = ["Knapsack", "Greedy", "Subarray Sums"]
        logger.debug(f"fetch_problems returned {len(result)} problems")
        return result
    except Exception as e:
        error_handler.handle_tool_error("fetch_problems", e)
        raise
