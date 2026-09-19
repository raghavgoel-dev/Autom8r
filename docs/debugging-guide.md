# Autom8r Debugging Guide

This guide teaches a method, then applies it to every failure mode you are
likely to hit with this project. Keep two habits: read the actual error
message before changing anything, and change one thing at a time.

## The method

1. **Reproduce.** Run the exact command or request that fails, and capture
   the full output. "It doesn't work" is not a reproduction;
   `curl http://localhost:8000/health` returning a connection refused is.
2. **Isolate.** Which process is failing: the browser, the backend (port
   8000), or the MCP server (port 8001)? Check each one independently. The
   health endpoint and `GET /api/v1/admin/tools` exist precisely for this.
3. **Inspect.** Read the backend console (every request is logged with
   method, path, status, and duration) and the traceback. The client always
   gets a safe envelope; the DETAIL is in the logs by design.
4. **Fix.** Change the one thing the evidence points to.
5. **Retest.** Re-run the reproduction from step 1, then run the test
   suites: `pytest` in `backend/` (58 tests) and in `mcp_server/` (9 tests).

---

## FastAPI won't start

**Symptoms:** `uvicorn app.main:app --reload --port 8000` exits immediately,
or `uvicorn` is not recognized, or `ModuleNotFoundError`.

**Likely causes and fixes:**

- Wrong working directory. The command must run from `backend/` (that is
  where the `app` package lives). `cd backend` first.
- Dependencies not installed, or installed into a different Python. Create
  and activate the venv, then install:
  ```powershell
  cd backend
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
  Confirm with `pip show fastapi` (expected: 0.141.1 or compatible).
- A broken `.env`. `Settings` parses `backend/.env` at import time, so a
  malformed value (for example `BACKEND_PORT=abc`) fails at boot with a
  pydantic validation error naming the field. Fix the value or delete the
  line; every setting has a working default.
- Port already in use: see the dedicated section below.

**Inspect:** the traceback names the missing module or the bad setting.
Boot logs one line on success:
`autom8r backend up: env=development llm_mode=mock mcp=http://127.0.0.1:8001/mcp`.

## Frontend can't connect to the backend

**Symptoms:** the browser shows a network error, `ERR_CONNECTION_REFUSED`,
or responses never arrive.

**Isolate:**

1. Is the backend up? `curl http://localhost:8000/health` should return
   `{"status":"ok",...}`.
2. Is the frontend calling the right URL? The base URL comes from
   `VITE_API_BASE_URL` (default `http://localhost:8000`). A stale Vite dev
   server caches env values; restart it after changing `.env`.
3. Is it actually CORS? See the next section.

**Fix:** start the backend, correct `VITE_API_BASE_URL`, restart the dev
server.

## CORS error in the browser console

**Symptom:** "Access to fetch ... has been blocked by CORS policy".

**Cause:** the browser only allows cross-origin calls from origins the
server explicitly lists. The backend allows exactly the origins in
`CORS_ORIGINS` (default `http://localhost:5173`), with credentials.

**Inspect:** check the page's origin in the browser address bar (including
the port) and compare with `CORS_ORIGINS` in `backend/.env`. A dev server on
`http://localhost:5174` or `http://127.0.0.1:5173` is a DIFFERENT origin
from `http://localhost:5173`.

**Fix:** add the exact origin, comma-separated, and restart the backend:
`CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`. Do not use `*`
with credentials; browsers reject that combination and it is unsafe anyway.

## LLM key missing / live mode not engaging

**Symptom:** `GET /health` reports `"llm_mode": "mock"` even though you set
`LLM_ENABLED=true`.

**Cause:** live mode requires BOTH `LLM_ENABLED=true` AND a non-empty
`LLM_API_KEY` (`Settings.llm_mode` in `backend/app/config.py`). With either
missing, the factory quietly builds the mock. This is deliberate: the demo
must run keyless.

**Inspect:** the boot log line says `LLM mode: MOCK (set LLM_ENABLED=true +
LLM_API_KEY for live)` or `LLM mode: LIVE (model=...)`.

**Fix:** set both in `backend/.env`, plus `LLM_BASE_URL` / `LLM_MODEL` if
you are not using OpenAI directly, and restart. Note the safety net: if the
live call fails at runtime, that turn falls back to mock and the response
reports `llm_mode: "mock"`. Check the backend log for
`live LLM failed ... falling back to mock`.

## MCP connection failure (503 MCP_UNAVAILABLE)

**Symptoms:** `GET /api/v1/admin/tools` returns
`{"success":false,"error":{"code":"MCP_UNAVAILABLE",...}}`, or chat replies
say the lead-recording service is temporarily unavailable with an `error`
entry in `tool_activity`.

**Cause:** the backend cannot reach the MCP server at `MCP_SERVER_URL`
(default `http://127.0.0.1:8001/mcp`). Any SDK or transport failure is
converted to `MCPUnavailableError` on purpose, so 503 means "connection
problem", never "the tool ran and failed" (that is 502 `MCP_TOOL_ERROR`).

**Isolate:**

1. Is the MCP server running? From the repo root:
   `python -m mcp_server.server`. It must stay running in its own terminal.
2. Is it on the expected port? Default 8001; `MCP_PORT` changes it.
3. Does `MCP_SERVER_URL` in `backend/.env` match, including the `/mcp` path?

**Fix:** start the server, or correct the URL. No backend restart is needed
for the next call to succeed, because every tool call opens a fresh
connection (the per-call design exists exactly so a restarted server leaves
nothing stale behind).

## MCP tool not found / tool errors

**Symptoms:** a tool call returns `is_error`, the backend logs
`mcp tool <name> failed`, or the API surfaces 502 `MCP_TOOL_ERROR`.

**Likely causes:**

- **Unknown tool name.** The server exposes exactly four:
  `create_lead`, `search_lead`, `update_lead`, `get_business_info`. Verify
  with `GET /api/v1/admin/tools` or the MCP Inspector. A live LLM that
  hallucinates a tool name lands here too; the error is fed back to the
  model as a `{"success": false, ...}` tool result.
- **Tool-level business error.** Example: `update_lead` with a phone that
  does not exist raises `ValueError("no lead found with phone ...")` inside
  the tool, which the SDK reports as a tool error. The fix is in the data or
  the arguments, not the transport: search first, then update.

**Inspect:** `GET /api/v1/admin/tools` for the live tool list; the backend
log line `mcp tool <name> failed: <detail>` for the server's own message.

## "database is locked"

**Symptom:** `sqlite3.OperationalError: database is locked` from either
process.

**Cause:** two processes share `data/autom8r.db`. Without WAL, one writer
locks the whole file. This project already enables the fix on BOTH sides:
`PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=15000` on every
connection (`backend/app/db/database.py` and `mcp_server/db.py`). If you
still see the error, the usual reasons are:

- A third program has the file open (a SQLite GUI, a stray Python REPL that
  opened the database). Close it.
- You deleted `data/autom8r.db` while a process held it, leaving stale
  `-wal` / `-shm` files. Stop both processes, delete
  `data/autom8r.db*` (all three files), and restart; tables are recreated on
  boot.
- A long-running write transaction in hand-written code. Keep transactions
  short; both data layers in this repo commit immediately per operation.

**Verify the mode:** `sqlite3 data\autom8r.db "PRAGMA journal_mode;"` should
print `wal`.

## Invalid JSON (client side)

**Symptom:** 422 with the standard envelope, or the request never parses.

**Cause:** the body is not valid JSON, or `Content-Type: application/json`
is missing, or a PowerShell quoting issue mangled the payload (single vs
double quotes are the classic one).

**Inspect:** the backend logs the first validation error with field detail;
the client only gets the generic envelope by design (no schema internals
leak). In PowerShell, prefer `-d (Get-Content file.json -Raw)` over inline
JSON, as the smoke test in `docs/api-reference.md` does.

## 422 VALIDATION_ERROR

**Symptom:** `{"success":false,"error":{"code":"VALIDATION_ERROR","message":"Request payload failed validation"}}`.

**Cause:** Pydantic rejected the payload before the route ran. Common
triggers: missing `name` or `phone` on lead creation; a phone with fewer
than 7 or more than 15 digits after normalization; a blank name; `limit=0`
or `limit=500` on list endpoints; an unknown `status` value in a PATCH; an
empty chat `message`; a webhook `event` other than `"lead.created"`.

**Inspect:** the backend log line `validation error: ...` names the exact
field and rule. The client gets the generic message on purpose.

**Fix:** correct the payload per `docs/api-reference.md`. Remember phones
are normalized: `+91 98765-43210` is fine, `123` is not.

## 401 UNAUTHORIZED (admin and webhook)

**Symptom:** `{"success":false,"error":{"code":"UNAUTHORIZED",...}}` from
`/api/v1/admin/*` or `/api/v1/webhooks/lead`.

**Causes and fixes:**

- Admin routes need `Authorization: Bearer <ADMIN_TOKEN>`. Check the header
  name, the `Bearer ` prefix (with the space), and that the token matches
  `ADMIN_TOKEN` in `backend/.env` exactly (the default is `change-me`).
- The webhook route needs `X-Webhook-Secret: <WEBHOOK_SECRET>`. Same
  exact-match rule.
- Both comparisons use `hmac.compare_digest` (constant time), so "close
  enough" never passes; whitespace and case must match.

**Inspect:** the message in the envelope tells you which check failed
("missing or malformed Authorization header" vs "invalid admin token", and
the webhook equivalents).

## 404 LEAD_NOT_FOUND

**Symptom:** `{"success":false,"error":{"code":"LEAD_NOT_FOUND","message":"Lead 42 not found"}}`.

**Cause:** no lead with that id. Ids are auto-increment and are not reused
after deletes.

**Inspect:** `GET /api/v1/leads?limit=100` to see what exists. If the
database looks empty when you expect data, check whether you seeded it
(`python -m app.db.seed` from `backend/`) and whether you are pointing at
the database you think you are (`DATABASE_URL`; tests deliberately use a
throwaway file).

## 500 INTERNAL_ERROR

**Symptom:** `{"success":false,"error":{"code":"INTERNAL_ERROR","message":"Something went wrong on our side"}}`.

**Cause:** an unhandled exception reached the last-resort handler in
`app/main.py`. The client message is generic on purpose; the full traceback
is in the backend console (look for `unhandled error:`).

**Fix:** read the traceback, fix the root cause, and add a typed error in
`app/utils/errors.py` if the failure is a known category that deserves its
own status code. Then retest.

## Google Sheets sync failure

**Symptom:** the lead is created fine, but nothing appears in the Google
Sheet, and the backend logs `sheets sync failed for lead <id>: ...`.

**Cause:** the adapter is best-effort by design. It only runs when ALL of
`GOOGLE_SHEETS_ENABLED=true`, `GOOGLE_SERVICE_ACCOUNT_JSON`, and
`GOOGLE_SHEET_ID` are set, and any failure (bad credentials path, invalid
inline JSON, wrong sheet id, missing share with the service account, network
error) is logged and swallowed so the core flow never breaks. The lead is
already safe in SQLite.

**Inspect:** the warning log names the underlying exception. Also confirm
`gspread` and `google-auth` are installed; they are commented out in
`requirements.txt` because the base install has no Google dependencies.

**Fix:** correct the credentials (a file path OR the inline JSON string),
share the sheet with the service-account email, verify the sheet id, and
retry by creating a new lead. A production hardening would add a retry
queue; the current code documents that as a deliberate tradeoff.

## Port already in use (Windows)

**Symptom:** `error while attempting to bind on address ('127.0.0.1', 8000):
[WinError 10048]` (or the same for 8001 / 5173).

**Inspect:** find which process owns the port:

```powershell
netstat -ano | findstr :8000
```

The last column is the PID. Identify it:

```powershell
Get-Process -Id <PID>
```

**Fix:** stop the process (often a previous uvicorn or a crashed Python that
never released the socket):

```powershell
taskkill /PID <PID> /F
```

Then start the server again. If the port is genuinely needed by something
else, move this app instead: `--port 8002` for uvicorn, `MCP_PORT=8002` for
the MCP server (and update `MCP_SERVER_URL` to match).

---

## When all else fails

Run the suites. They encode the verified behavior of the whole system:

```powershell
cd backend; pytest          # 58 passed
cd ..\mcp_server; pytest    # 9 passed
```

Green tests plus a failing manual run means the difference is in your
environment or your request, and the test files (`backend/tests/`,
`mcp_server/tests/test_server.py`) show the exact known-good requests to
compare against.
