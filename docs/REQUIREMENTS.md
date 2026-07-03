# CSES MCP Server — Requirements

## 1. Purpose

An MCP (Model Context Protocol) server that lets an AI assistant act on a
user's behalf on [CSES](https://cses.fi) (Code Submission Evaluation
System): browsing problems, checking submission status/history, retrieving
old submitted code, and submitting new solutions.

This is a personal-use tool. CSES has no public API — all data access is
via scraping authenticated HTML pages and posting to existing web forms
using the user's own session.

## 2. Goals

- Let a user query their CSES submission history and problem status from
  within an MCP-compatible client (e.g. Claude Code) without opening a
  browser.
- Let a user fetch the source code of a past submission (their own).
- Let a user submit a solution file to a CSES problem and check the
  resulting verdict.
- Let a user browse/search the CSES problem list (name, tags/category,
  difficulty if available, solved/unsolved status).

## 3. Non-Goals

- No support for accounts other than the authenticated user's own.
- No CAPTCHA-solving or automated account creation.
- No scraping of other users' submissions/code (CSES only exposes your own
  submission source for problems you've solved, and that's the only case
  this tool should touch).
- No high-frequency polling / bulk scraping that could be mistaken for
  abuse. Requests should be on-demand, user-initiated, and rate-limited.
- Not an offline judge — no local test-case execution or grading.

## 4. Authentication

- CSES uses cookie-based session auth (login form + `PHPSESSID`-style
  cookie). There is no OAuth/token flow.
- The user logs in once (either by the tool driving the login form with
  username/password, or by the user pasting an existing session cookie),
  and the resulting session cookie is persisted **locally only**.
- Credentials/cookies must never be logged, printed in tool output, or
  transmitted anywhere except cses.fi.
- Session expiry must be detected (e.g. redirect to login page) and
  surfaced as a clear "please re-authenticate" error rather than a silent
  failure or misparsed page.

## 5. Libraries

- `fastmcp` — standalone FastMCP package (not the bundled
  `mcp.server.fastmcp`), chosen for its extra features (auth providers,
  client testing utilities) that may be useful for the CSES login flow.
  Pulls in the official `mcp` SDK as a dependency.
- `httpx` — async HTTP client, holds the CSES session cookie.
- `beautifulsoup4` + `lxml` — HTML parsing for scraping problem/status
  pages.
- Dev: `pytest`, `ruff`.

## 6. Functional Requirements (MCP Tools)

| Tool | Description |
|---|---|
| `login` / `set_session` | Establish a CSES session (credentials or cookie import). |
| `list_problems` | List problems, optionally filtered by category, with solved/unsolved status for the logged-in user. |
| `get_problem` | Fetch a single problem's statement, constraints, and the user's current status for it. |
| `get_submission_history` | List past submissions (problem, verdict, time, language), optionally filtered by problem. |
| `get_submission_code` | Retrieve the source code of a specific past submission. |
| `submit_solution` | Submit a solution (source code + language) to a given problem and return the new submission id. |
| `get_submission_result` | Poll a submission id for verdict/test-case results until it's done judging. |

## 7. Non-Functional Requirements

- **Resilience to markup changes**: HTML parsing should be isolated in a
  single client layer so that CSES front-end changes require updates in
  one place, and failures degrade to a clear "page format changed,
  scraping broke" error rather than wrong data.
- **Rate limiting / politeness**: requests should be throttled and
  sequential, not parallelized against cses.fi.
- **No persistence of problem/submission data beyond the session cache**
  unless the user explicitly asks for it — this tool reflects live CSES
  state, it isn't a database.
- **Clear error surfaces**: distinguish between "not logged in",
  "network/site error", "page structure changed", and "submission
  rejected" so the assistant can react appropriately.

## 8. Open Questions

- Login flow: drive the HTML login form directly, or ask the user to
  supply a session cookie copied from their browser? (Cookie import is
  simpler and avoids handling raw passwords, but is less convenient.)
- Where/how is the session cookie persisted between runs (e.g. local file
  under an OS-appropriate config dir) and how is it protected at rest?
- Submission language detection: inferred from file extension, or passed
  explicitly as a tool argument?
- Should `get_submission_result` block/poll internally, or return
  immediately and require the caller to poll `get_submission_result`
  again?
