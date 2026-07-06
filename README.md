# CSES MCP Server

*Your AI assistant's gateway to [CSES](https://cses.fi) (Code Submission Evaluation System)* 🧩

## 🤔 What is this?

`cses-mcp` is a Python-based MCP (Model Context Protocol) server that lets
an MCP-compatible client (like Claude Desktop or Claude Code) act on your
behalf on CSES: browsing problems, reading problem statements, submitting
solutions, and checking submission history/verdicts.

As far as I know, CSES has no public API, so all data access is via scraping authenticated HTML
pages and posting to existing web forms using your own session cookie.

### Why?

CSES is one of the best free problem sets for learning competitive
programming, but working through it usually means a lot of manual tab-
switching: reading a statement, writing code elsewhere, coming back to
submit, then digging through a verdict page to figure out what went wrong.
This project turns that whole loop into a conversation — ask an AI
assistant to find you a problem, explain the statement, help you reason
through an approach, submit your solution, and diagnose a wrong verdict,
all without leaving the chat. The goal isn't to solve problems *for* you
(though it can) — it's to make the feedback loop tight enough that you
actually learn faster: get hints instead of full solutions when you want
them, understand *why* a submission got Wrong Answer or Time Limit
Exceeded, and use past-attempt history to see your own progress over time.

---

## 🚀 Quick Start

Pick whichever fits — Option A if you just want to use it, Option B if
you're editing the code.

### Option A — Copy-paste (no local clone)

Paste this straight into your MCP client config — `uvx` fetches and runs
the published package, no clone, no `uv sync`, no `.env` file to manage:

```json
{
  "mcpServers": {
    "cses-mcp": {
      "command": "uvx",
      "args": ["qhung-cses-mcp@latest"],
      "env": {
        "PHPSESSID": "<your CSES session cookie>"
      }
    }
  }
}
```

Requirements:
- [`uv`](https://docs.astral.sh/uv/) installed (`uvx` ships with it):
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- Your `PHPSESSID` pasted into the `env` block above — see
  [Getting your CSES session cookie](#getting-your-cses-session-cookie).

Restart your MCP client and the tools are available — that's it.

<details>
<summary>Not on PyPI yet, or want to track the repo directly instead?</summary>

Point `--from` at a plain HTTPS archive of the repo instead of the
published package — still no `git clone`, no `uv sync`, and (unlike a
`git+` URL) no local `git` executable required at all, which matters if
your MCP client runs in a sandboxed environment (e.g. Claude Desktop's
Windows package can't execute `git` even when it's installed and on
`PATH`):

```json
{
  "mcpServers": {
    "cses-mcp": {
      "command": "uvx",
      "args": ["--from", "https://github.com/qhung23125005/CSES-MCP/archive/refs/heads/master.tar.gz", "qhung-cses-mcp"],
      "env": {
        "PHPSESSID": "<your CSES session cookie>"
      }
    }
  }
}
```

A `--from git+https://github.com/qhung23125005/CSES-MCP` URL also works if
you want it to always resolve via git instead, but that requires a working
local `git` that your MCP client's process can actually execute — see
[Option B](#option-b--manual-clone-for-local-development--editing-the-code)
if neither of these is reliable in your environment.
</details>

### Option B — Manual clone (for local development / editing the code)

1. **Prerequisites** — Python 3.12+ and `uv` (see the install commands above).
2. **Clone and install:**
   ```bash
   git clone https://github.com/qhung23125005/CSES-MCP.git
   cd CSES-MCP
   uv sync --all-extras
   cp .env.example .env
   ```
3. **Add your `PHPSESSID` to `.env`** — see
   [Getting your CSES session cookie](#getting-your-cses-session-cookie).
4. **Run it standalone** (for manual testing / the MCP Inspector):
   ```bash
   make run              # STDIO transport (default)
   make run-debug        # STDIO with debug logging
   make run-sse          # SSE transport on port 8000
   make run-inspector     # Run with the MCP Inspector (browser UI to call tools manually)
   ```
5. **Or connect an MCP client** to the cloned copy:
   ```json
   {
     "mcpServers": {
       "cses-mcp": {
         "command": "uv",
         "args": ["run", "--project", "/path/to/CSES-MCP", "python", "-m", "cses_mcp.main"]
       }
     }
   }
   ```
   `--project` pins `uv` to this project's environment regardless of the
   working directory the client spawns from — more reliable than a `cwd`
   setting. `.env` is resolved relative to the project root automatically
   (see `src/cses_mcp/config/settings.py`), so no `env` block is needed in
   the client config — though you can still use one instead of `.env` if
   you prefer, the same way Option A does.

### Getting your CSES session cookie

The server authenticates as you using your CSES session cookie
(`PHPSESSID`) — no tool ever takes a password or cookie as an argument, so
an AI assistant calling these tools never sees or handles the credential
itself.

1. Log into [cses.fi](https://cses.fi) in your browser.
2. Open DevTools (`F12`) → **Application** (Chrome/Edge) or **Storage**
   (Firefox) → **Cookies** → `https://cses.fi`.
3. Copy the `PHPSESSID` value — into the client config's `env` block
   (Option A) or into `.env` (Option B).

CSES sessions can expire; if tools start returning `CSES_NOT_AUTHENTICATED`,
re-copy a fresh cookie.

You're ready! Start issuing prompts via your MCP client — see
[💬 Example Prompts for Claude](#-example-prompts-for-claude).

---

## 🛠️ Available Tools

*(Input parameters are strings unless otherwise specified)*

- **`fetch_categories`** *(no auth)*: List every CSES problem category name (e.g. "Introductory Problems", "Sorting and Searching").
  - _Returns:_ List of category name strings.
- **`fetch_problems`** *(auth required)*: List problems, optionally filtered by category/status, with your solve status for each.
  - `category` (optional string): Exact category name, case/whitespace-insensitive (use `fetch_categories` to look one up).
  - `status` (optional string): One of `"completed"`, `"not accepted"`, `"not completed"`.
  - _Returns:_ List of `{name, link, status, category}`.
- **`fetch_problem_statement`** *(no auth)*: Fetch a single problem's statement.
  - `url` (string): Absolute problem page URL, e.g. `https://cses.fi/problemset/task/1068`.
  - _Returns:_ `{Title, Limit: {time_limit, memory_limit}, description, sections: {input, output, constraints, example}}`.
- **`submit_code`** *(auth required)*: Submit a solution to a task for judging.
  - `task_id` (string): The CSES task id, e.g. `"1068"`.
  - `filename` (string): Used only to infer language from its extension, e.g. `"solution.py"`. Supported: `.asm .c .cpp/.cc .hs .java .js .pas .py .rb .rs .scala`.
  - `code` (string): The full source code, in-memory — no filesystem access needed.
  - _Returns:_ `{task_id, submission_id, redirect}`.
- **`fetch_submission`** *(auth required)*: Fetch one submission's details, per-test verdicts, and submitted code.
  - `submission_id` (string): From `submit_code`'s response or a result URL.
  - _Returns:_ `{task, sender, submission_time, language, status, result, tests: [{test, verdict, time}], code}`.
- **`fetch_submission_list`** *(auth required)*: List your past submissions for a task, most recent first.
  - `task_id` (string): The CSES task id, e.g. `"2134"`.
  - _Returns:_ List of `{submission_id, time, lang, code_time, code_size, result}`.

Every tool returns a single error dict (`{"error": true, "error_code": ..., "message": ..., ...}`)
on failure instead of raising — check for `"error": true` before treating a
result as success. `"auth required"` tools need `PHPSESSID` set (see
[Getting your CSES session cookie](#getting-your-cses-session-cookie));
the others scrape public pages and work without one.

---

## 💬 Example Prompts for Claude

Once connected, try prompts like:

- "What CSES problem categories are there?"
- "List all problems in Sorting and Searching that I haven't solved yet."
- "Give me the statement for Weird Algorithm."
- "Submit this Python solution to task 1068: `<code>`."
- "Was my last submission to Path Queries II accepted? If not, what verdict did it get?"
- "Show me the code I submitted for submission 17833364."
- "How many times have I submitted to task 2134, and what were the results?"
- "Find an easy problem I haven't solved in Dynamic Programming, show me the statement, and help me write a solution."
- "In my latest submission for Path Queries II, I got both WA and TLE. Identify the cause."
- "Complete the remaining unsolved problems in the Tree Algorithms category for me to use as reference."
- "Can you give me a hint on how to solve \<problem name\>?"

---

## 🧪 Testing

```bash
make test             # Run tests (mocked HTTP, no network, no credentials needed)
make test-cov         # Run tests with coverage
make lint             # Ruff lint
make format           # Ruff format/fix
```

Each tool's tests also include an opt-in **live smoke test** that hits the
real cses.fi site using your `.env` cookie — skipped by default, run with:
```bash
RUN_LIVE_TESTS=1 uv run pytest -k live
```

---

## 📁 Project Structure

```
src/cses_mcp/
├── __init__.py
├── main.py                    # CLI entry point
├── server.py                  # Core server implementation
├── client.py                  # Ad-hoc script for exercising the server locally
├── config/
│   └── settings.py            # Configuration management (pydantic-settings)
├── tools/                     # MCP tools
│   ├── fetch_categories_tools.py
│   ├── fetch_problems_tools.py
│   └── submission_tools.py
├── resources/                 # MCP resources (scaffolded, empty)
├── prompts/                   # MCP prompts (scaffolded, empty)
├── handlers/
│   └── error_handler.py       # Centralized tool error handling
└── utils/
    ├── logger.py
    └── validation.py

tests/
├── fixtures/                  # Saved sample CSES HTML pages used by unit tests
├── unit/                      # Mocked-HTTP tests + opt-in live smoke tests
└── integration/                # In-process MCP server/tool-registration tests
```

### Adding Tools, Resources, and Prompts

1. Create a new file under `src/cses_mcp/tools/` (or `resources/`, `prompts/`)
   using `from ..server import mcp` and the relevant `@mcp.tool` /
   `@mcp.resource` / `@mcp.prompt` decorator.
2. Register the module by importing it in that package's `__init__.py`.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and customize. See
[src/cses_mcp/config/settings.py](src/cses_mcp/config/settings.py) for all
available settings (server name, log level/file, debug mode, CSES base URL,
request timeout, `PHPSESSID`). Settings are read from real environment
variables first, `.env` second — so an MCP client can also inject
`PHPSESSID` via its own `"env"` config block instead of a committed `.env`
file.

---

## 🔒 Security

- `PHPSESSID` lives only in server-side config (`.env` or process env) and
  is never a tool argument — no tool call can expose it in conversation
  history, and error responses redact it from logged tool args.
- Session cookies/credentials must never be logged, printed in tool output,
  or transmitted anywhere except cses.fi.
- Requests to CSES should be sequential and rate-limited, not parallelized.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
