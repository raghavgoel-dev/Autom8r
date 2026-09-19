# Autom8r Learning Notes

One page per concept, in the order a fresher should learn them. Each entry
has five parts: WHAT IT IS, WHY WE USED IT, HOW IT WORKS IN AUTOM8R (with the
real files), WHAT CAN FAIL, and WHAT AN INTERVIEWER MAY ASK. Read these until
you can explain each one without opening the file.

---

## 1. Python

WHAT IT IS: A high-level, dynamically typed language with optional type
hints. The whole backend and the MCP server are Python 3.13.

WHY WE USED IT: The fastest path from idea to working AI integration: the
best LLM SDKs, FastAPI, and the official MCP SDK all live in Python first.

HOW IT WORKS IN AUTOM8R: Services are plain Python modules with one job each
(`backend/app/services/`). Data carriers are frozen dataclasses
(`LeadSignals` in `backend/app/services/scoring.py`, `ExtractedLead` in
`backend/app/services/extraction.py`). Type hints everywhere; pure stdlib in
the shared modules so the MCP process can import them.

WHAT CAN FAIL: Mutable default arguments leaking state, `==` vs `is`
confusion with `None`, import-time side effects (Autom8r's test config must
set env vars before importing the app, see `backend/tests/conftest.py`), and
circular imports between packages.

WHAT AN INTERVIEWER MAY ASK: list vs tuple, decorators, generators, the GIL,
exception handling, type hints, dataclasses. (See interview-questions.md,
Python section.)

---

## 2. FastAPI

WHAT IT IS: A modern Python web framework. You write typed functions;
FastAPI validates requests with Pydantic, generates OpenAPI docs, and runs
async on uvicorn.

WHY WE USED IT: Validation and API documentation for free, async-native for
an I/O-bound chat workload, and the most in-demand Python API framework in
2026.

HOW IT WORKS IN AUTOM8R: `backend/app/main.py` builds the app, wires services
onto `app.state` in a `lifespan` context, adds CORS and request-logging
middleware, installs three global exception handlers, and mounts five routers
from `backend/app/api/routes/`. Dependencies inject the DB session
(`get_db`), auth (`require_admin`, `verify_webhook_secret`), and settings.

WHAT CAN FAIL: Forgetting `response_model` (response shapes drift from the
contract), blocking the event loop with sync I/O in an async route, leaking
stack traces (handled here by the global handlers), and CORS misconfiguration
when the frontend origin is missing from `CORS_ORIGINS`.

WHAT AN INTERVIEWER MAY ASK: how dependency injection works, how validation
happens, middleware vs dependencies, how to return custom error shapes, what
`lifespan` replaces (the old `on_event` startup hooks).

---

## 3. REST

WHAT IT IS: An API style: resources at URLs, standard HTTP methods, stateless
requests, meaningful status codes.

WHY WE USED IT: The frontend needs a predictable contract, and REST over JSON
is the common language of web backends.

HOW IT WORKS IN AUTOM8R: `backend/app/api/routes/leads.py` demonstrates the
full verb set with correct codes: GET list (200, with filters as query
params), GET one (200/404), POST (201), PATCH (200, partial body), DELETE
(204). The shapes are frozen in `docs/api-contract.md`.

WHAT CAN FAIL: Wrong status codes (200 for everything is a red flag), verbs
that lie (a GET that deletes), pagination that skips rows, and contract drift
between doc and code.

WHAT AN INTERVIEWER MAY ASK: PUT vs PATCH, idempotency, status codes, how to
version, how to paginate.

---

## 4. HTTP

WHAT IT IS: The request-response protocol of the web: methods, headers,
status codes, bodies. Everything the frontend, the webhook sender, and the
MCP client do rides on it.

WHY WE USED IT: It is the substrate; you do not choose it so much as master
it.

HOW IT WORKS IN AUTOM8R: JSON bodies everywhere; `Authorization: Bearer` for
admin, `X-Webhook-Secret` for webhooks; the MCP client POSTs to
`http://127.0.0.1:8001/mcp` using Streamable HTTP; one log line per request
records method, path, status, and duration.

WHAT CAN FAIL: Missing `Content-Type` headers, auth headers dropped by
proxies, confusing 401 with 403, and assuming a request arrived exactly once
(retries are normal, hence idempotency).

WHAT AN INTERVIEWER MAY ASK: methods and their safety, headers you have used,
what happens in an HTTPS request, 401 vs 403, 502 vs 503.

---

## 5. JSON

WHAT IT IS: The text format for structured data on the wire: objects, arrays,
strings, numbers, booleans, null. No functions, no comments, no dates (dates
travel as ISO strings).

WHY WE USED IT: It is the default payload format for REST APIs, LLM tool
arguments, and MCP structured content.

HOW IT WORKS IN AUTOM8R: Every API body is JSON, parsed into Pydantic models.
Tool arguments cross the LLM boundary as JSON (`json.loads` on the model's
function arguments in `agent_service.py`). MCP tool results come back as
`structured_content`, which is JSON data, not text to parse.

WHAT CAN FAIL: Invalid JSON from an LLM (Autom8r guards with a
`json.JSONDecodeError` fallback to `{}`), date formats, encoding issues, and
trusting JSON structure without validating it (that is what Pydantic is for).

WHAT AN INTERVIEWER MAY ASK: JSON vs a Python dict, how to handle dates, what
happens with duplicate keys, how you validate untrusted JSON.

---

## 6. Pydantic

WHAT IT IS: A library that parses and validates untrusted data into typed
Python models. v2 is written in Rust and noticeably fast.

WHY WE USED IT: "Parse, don't validate": bad payloads are rejected at the API
boundary with a 422, so route functions only ever see clean data.

HOW IT WORKS IN AUTOM8R: Request/response schemas in `backend/app/schemas/`:
`LeadCreate` normalizes phone numbers with a `field_validator`, `LeadUpdate`
makes every field optional for PATCH, `ChatRequest` caps history at 50
messages. `model_config = ConfigDict(frozen=True)` makes schemas immutable.
pydantic-settings (`backend/app/config.py`) does the same job for environment
variables.

WHAT CAN FAIL: Validation errors leaking internals (Autom8r wraps 422s in a
generic envelope and logs the detail), forgetting `exclude_unset=True` on
PATCH (unset fields would overwrite with None), and confusing validators with
serializers.

WHAT AN INTERVIEWER MAY ASK: Pydantic v1 vs v2, how field validators work,
what `Field(ge=0)` means, how FastAPI uses Pydantic.
---

## 7. SQL

WHAT IT IS: The declarative language of relational databases: SELECT, INSERT,
UPDATE, DELETE, plus DDL for schema.

WHY WE USED IT: Leads are relational data with filters, search, and
aggregates; SQL is the right tool, and knowing it is non-negotiable in
interviews.

HOW IT WORKS IN AUTOM8R: Two idioms on purpose. The backend writes SQL
through SQLAlchemy (`backend/app/services/lead_service.py`: `select`, `where`,
`order_by`, `func.count`). The MCP server writes raw parameterized SQL by
hand (`mcp_server/db.py`: `?` placeholders, `LIKE` search, indexed columns).

WHAT CAN FAIL: SQL injection from string-built queries (never do it;
parameterize), missing indexes on filtered columns, N+1 queries, and schema
drift between the two writers (pinned by a test in
`mcp_server/tests/test_server.py`).

WHAT AN INTERVIEWER MAY ASK: JOIN types, WHERE vs HAVING, indexes and their
cost, injection prevention, GROUP BY with COUNT.

---

## 8. SQLite

WHAT IT IS: A serverless relational database: the whole database is one file,
no process, no network. ACID-compliant.

WHY WE USED IT: Zero-install demo and tests, and a real engineering story:
two processes sharing one file safely.

HOW IT WORKS IN AUTOM8R: The file is `data/autom8r.db`. Both processes set
`PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=15000` on every connection
(`backend/app/db/database.py`, `mcp_server/db.py`). WAL lets readers and one
writer work concurrently; the busy timeout makes a locked writer wait instead
of erroring. The backend also sets `check_same_thread=False` because FastAPI
serves requests on a thread pool.

WHAT CAN FAIL: "database is locked" without WAL or with long write
transactions, datetime format mismatches between writers (the MCP side writes
SQLAlchemy's exact storage format on purpose), and hitting SQLite's ceiling:
many concurrent writers or multiple machines.

WHAT AN INTERVIEWER MAY ASK: when SQLite is appropriate, what WAL mode does,
SQLite vs PostgreSQL, how two processes can share one file.

---

## 9. SQLAlchemy

WHAT IT IS: Python's standard ORM and SQL toolkit. Version 2.0 style uses
`Mapped[...]` annotations and `mapped_column`.

WHY WE USED IT: Object-oriented data access with safe query composition,
per-request sessions, and a one-line path to PostgreSQL later (change
`DATABASE_URL`).

HOW IT WORKS IN AUTOM8R: `backend/app/db/database.py` builds the engine and
sets SQLite pragmas on connect. `backend/app/models/lead.py` and
`webhook_event.py` declare tables. `backend/app/db/session.py` gives one
short-lived session per request via a generator dependency. Services compose
queries with `select()`; routes stay thin.

WHAT CAN FAIL: Forgetting to commit, stale objects after commit (Autom8r
calls `db.refresh(lead)`), N+1 queries on relationships, and engine state
created at import time (why tests set env vars before importing the app).

WHAT AN INTERVIEWER MAY ASK: ORM vs raw SQL, what a session is, how
migrations work (Alembic), 1.x vs 2.0 style.

---

## 10. React

WHAT IT IS: A UI library: components as functions of props and state,
re-rendered on state change, diffed onto the DOM.

WHY WE USED IT: The demo needs an interactive chat UI with a lead panel and a
tool-activity panel, and React 18 is the most requested frontend skill.

HOW IT WORKS IN AUTOM8R: A Vite-served SPA in `frontend/` (React 18). The
page owns conversation state; each send posts `{message, history}` to
`POST /api/v1/chat`; the response re-renders three areas: the chat thread
(`reply`), the lead panel (`lead`), and the activity panel (`tool_activity`).
An honest "Mock LLM" badge reads `llm_mode`.

WHAT CAN FAIL: Stale state in async handlers, missing keys on lists, effects
without cleanup (double fetches in StrictMode), and unhandled error states
(spinners forever).

WHAT AN INTERVIEWER MAY ASK: props vs state, useEffect and its cleanup, keys,
controlled forms, what triggers a re-render.

---

## 11. TypeScript

WHAT IT IS: JavaScript plus static types, checked at build time and erased at
runtime.

WHY WE USED IT: The API contract is typed on the Python side; TypeScript
keeps the same discipline on the frontend, so contract mismatches fail at
build time.

HOW IT WORKS IN AUTOM8R: `frontend/src/types/` mirrors the frozen shapes in
`docs/api-contract.md` (`LeadOut`, `ChatResponse`, `ToolActivityItem` as
interfaces; `priority` and `llm_mode` as string-literal unions).
`frontend/src/services/` owns the `fetch` calls so components never build
URLs or parse loosely typed responses.

WHAT CAN FAIL: `any` creeping in and defeating the point, types drifting from
the real API (the contract doc is the guard), and over-engineering types
instead of modeling the actual data.

WHAT AN INTERVIEWER MAY ASK: interface vs type, union types, strict mode,
optional chaining, how to type an API response.

---

## 12. async/await

WHAT IT IS: Cooperative concurrency. `async def` defines a coroutine; `await`
yields control while I/O completes, so one thread juggles many operations.

WHY WE USED IT: A chat turn is pure I/O waiting: LLM call, MCP call,
database. Async serves many concurrent chats on one process without threads.

HOW IT WORKS IN AUTOM8R: The chat route is `async def`
(`backend/app/api/routes/chat.py`), the agent awaits MCP calls
(`AgentService._run_live`, `_run_mock`), and the MCP client is async
end to end (`async with Client(...)` in `mcp_client_service.py`). The MCP
server tests are async too, run by pytest-asyncio.

WHAT CAN FAIL: Calling a blocking function inside async code (it freezes the
loop), forgetting `await` (you get a coroutine object, not a result), and
mixing sync DB drivers into async routes (Autom8r keeps SQLAlchemy work in
sync routes, which FastAPI runs on a thread pool).

WHAT AN INTERVIEWER MAY ASK: async vs threads vs processes, what the event
loop is, what happens if you block it, when async does NOT help (CPU-bound
work).

---

## 13. LLM (Large Language Models)

WHAT IT IS: A model that predicts the next token, trained on massive text.
It generates fluent language and can follow instructions, but it has no
guaranteed facts and no memory beyond the context you send.

WHY WE USED IT: The product idea, an assistant that answers questions and
qualifies leads in natural language, is exactly what LLMs are good at.

HOW IT WORKS IN AUTOM8R: Behind an interface. `LLMService` is a protocol in
`backend/app/services/llm_service.py` with two implementations:
`OpenAILLMService` (any OpenAI-compatible endpoint via `LLM_BASE_URL`, model
default `gpt-4o-mini`) and `MockLLMService` (a deterministic policy, no
network). `build_llm_service()` picks from settings.

WHAT CAN FAIL: Provider outages (handled: automatic fallback to mock with an
honest `llm_mode` badge), hallucinated facts (handled: retrieval grounding
plus prompt rules), runaway tool loops (handled: `MAX_TOOL_ROUNDS = 3`), and
cost surprises from unbounded context.

WHAT AN INTERVIEWER MAY ASK: tokens, temperature, context window,
hallucination and mitigation, how you test LLM features, cost drivers.

---

## 14. System Prompts

WHAT IT IS: The standing instructions the model sees before any user message:
role, rules, boundaries. The highest-impact text in an LLM feature.

WHY WE USED IT: Behavior you can edit without deploying code, and a single
place where honesty rules live (never invent data, never claim a failed
action succeeded).

HOW IT WORKS IN AUTOM8R: Two files, not code:
`backend/app/prompts/system_prompt.txt` (11 rules: be concise, prefer
retrieved knowledge, use tools for actions, never reveal internals, escalate
to humans) and `backend/app/prompts/qualification_prompt.txt` (the lead
fields to collect and in what order). `load_prompts()` reads them per turn;
the same qualification guidance is also exposed as an MCP prompt for other
hosts.

WHAT CAN FAIL: Prompts that contradict the retrieval or the tools, secrets
accidentally pasted into prompts, and prompt injection from user input
(defended by rule 7 and by treating retrieved text as data).

WHAT AN INTERVIEWER MAY ASK: system vs user prompt, what belongs in a system
prompt, how you keep prompts maintainable, prompt injection.

---

## 15. Tool Calling (Function Calling)

WHAT IT IS: The model emits a structured call (name plus JSON arguments)
instead of text; your code executes it and returns the result; the model
composes the final answer from real data.

WHY WE USED IT: An assistant that "creates a lead" must actually create one.
Tools turn language into action with a verifiable result.

HOW IT WORKS IN AUTOM8R: In live mode, `AgentService._openai_tools()`
discovers MCP tools and converts their JSON Schemas into OpenAI function
schemas; `_run_live()` loops: completion, tool calls, MCP execution, tool
messages, repeat, capped at 3 rounds. In mock mode the same MCP tools are
called by the deterministic policy, so tests exercise the real tool path.

WHAT CAN FAIL: Bad arguments from the model (JSON parse fallback to `{}`),
tool failures mid-loop (returned to the model as an error payload so it can
respond honestly), infinite loops (the round cap), and the model claiming
success without calling (prompt rule 6 forbids it).

WHAT AN INTERVIEWER MAY ASK: the tool-calling loop step by step, how schemas
reach the model, how you stop runaway loops, how you test it.

---

## 16. Agents

WHAT IT IS: A decide-act-observe loop around an LLM: the model chooses
actions, tools execute them, results feed back, until the task is done or a
stop condition hits.

WHY WE USED IT: Lead qualification is a multi-step job (converse, extract,
decide, record, confirm), which is agent-shaped, not single-completion
shaped.

HOW IT WORKS IN AUTOM8R: `AgentService.handle_chat()`
(`backend/app/services/agent_service.py`) is the loop for one turn: retrieve
knowledge, accumulate extracted fields, decide (mock policy or live model),
execute via MCP, compose the reply, and report every side effect in
`tool_activity` so the UI can show what happened.

WHAT CAN FAIL: Loops that never terminate (round cap), actions taken on
wrong assumptions (tool results are the only truth; the UI shows them), and
opacity (mitigated by the activity panel and per-call logging).

WHAT AN INTERVIEWER MAY ASK: what makes something an agent vs a chatbot, how
you bound an agent, how you observe what it did, failure modes.

---

## 17. RAG (Retrieval-Augmented Generation)

WHAT IT IS: Retrieve relevant passages from your own documents, put them in
the prompt, and have the model answer from them. Grounding instead of
guessing.

WHY WE USED IT: The assistant must answer from this company's documents
(pricing, refund policy, products), which no base model knows, and the
answers must stay correct when the documents change.

HOW IT WORKS IN AUTOM8R: `backend/app/services/retrieval_service.py` splits
`data/knowledge/*.md` on `## ` headings into chunks, builds TF-IDF vectors,
and returns the top 3 by cosine similarity. A score under 0.15 counts as "no
knowledge". The agent injects strong matches into the system prompt as the
source of truth, and the mock policy answers directly from the top chunk,
citing the document name.

WHAT CAN FAIL: Paraphrase misses (keyword search cannot match "money back"
to "refund"; the embedding upgrade path is documented), stale chunks after
doc edits (re-indexed lazily per process), and over-retrieval polluting the
prompt (threshold plus top-k cap).

WHAT AN INTERVIEWER MAY ASK: the RAG pipeline, chunking strategy, keyword vs
vector search, when you need a vector DB, how you measure retrieval quality.

---

## 18. MCP (Model Context Protocol)

WHAT IT IS: An open protocol that standardizes how AI hosts discover and call
external capabilities: tools (functions), resources (readable data), and
prompts (templates), over stdio or Streamable HTTP.

WHY WE USED IT: It is where the industry is going for agent-tooling, it
forces a clean boundary between the model and the data, and it makes the
tools reusable by any MCP host, not just this backend.

HOW IT WORKS IN AUTOM8R: `mcp_server/server.py` builds an `MCPServer`
(SDK `mcp` 2.2.0, from `mcp.server.mcpserver`) with 4 tools, 1 resource
(`business://company-info`), and 1 prompt, served over Streamable HTTP on
port 8001 at path `/mcp`. The backend connects per call with `Client` from
`mcp.client` (`backend/app/services/mcp_client_service.py`). Tests connect
in-process: `Client(server, mode="legacy")`.

WHAT CAN FAIL: Server down (typed `MCPUnavailableError` becomes a 503
envelope; chat degrades but keeps answering), tool-reported errors
(`is_error` becomes `MCPToolError`, a 502), SDK churn (isolated behind the
`MCPClientLike` protocol), and schema drift with the backend (pinned by a
test).

WHAT AN INTERVIEWER MAY ASK: what MCP is, tools vs resources vs prompts,
transports, why MCP over direct API calls, how you test a server, what
happens when it is down.
---

## 19. Webhooks

WHAT IT IS: The inverse of an API call: an external system calls YOUR
endpoint when an event happens. "Something occurred; here is the payload."

WHY WE USED IT: A CPaaS-flavored demo needs one: lead-capture forms, delivery
receipts, and CRM events all arrive as webhooks in the real world.

HOW IT WORKS IN AUTOM8R: `POST /api/v1/webhooks/lead`
(`backend/app/api/routes/webhooks.py`) accepts a `lead.created` event
(`backend/app/schemas/webhook.py`). Security: the `X-Webhook-Secret` header,
compared in constant time. Idempotency: the `webhook_events` ledger table
(`backend/app/models/webhook_event.py`) records each `event_id`; a
redelivery gets 200 with `duplicate: true` instead of a second lead. A sample
payload lives at `data/samples/sample_webhook.json`.

WHAT CAN FAIL: Replay (duplicate deliveries; handled by the ledger), forged
requests (handled by the shared secret; production would sign the body with
HMAC), slow processing (production would ack fast and process async), and
leaked secrets in logs.

WHAT AN INTERVIEWER MAY ASK: webhook vs API, how you secure one, what
idempotency is and how you implement it, what a retry storm does.

---

## 20. Authentication

WHAT IT IS: Proving who the caller is. "Who are you?" Failed authentication
is a 401.

WHY WE USED IT: Admin stats and inbound webhooks must not be open to the
internet, even in a demo.

HOW IT WORKS IN AUTOM8R: Two demo mechanisms in
`backend/app/utils/security.py`: a Bearer token for `/api/v1/admin/*`
(`require_admin`) and a shared secret header for webhooks
(`verify_webhook_secret`). Both compare with `hmac.compare_digest`, a
constant-time comparison that defeats timing attacks. Tokens come from env
vars (`ADMIN_TOKEN`, `WEBHOOK_SECRET`), never from code.

WHAT CAN FAIL: Timing leaks (mitigated by `compare_digest`), tokens in
source control (`.env` is gitignored; `.env.example` holds placeholders),
and over-trusting a demo scheme (the docs state plainly this is demo auth,
not OAuth).

WHAT AN INTERVIEWER MAY ASK: Bearer tokens, constant-time comparison and why,
where secrets live, how this differs from OAuth2/JWT (the production answer).

---

## 21. Authorization

WHAT IT IS: Deciding what an authenticated caller may do. "Now that I know
who you are, what are you allowed to touch?" Failed authorization is a 403.

WHY WE USED IT: Honestly, Autom8r keeps it minimal on purpose: one admin
token, no roles, so only 401 exists today. Knowing where authorization WOULD
go is the interviewable part.

HOW IT WORKS IN AUTOM8R: The router-level dependency
(`dependencies=[Depends(require_admin)]` in `backend/app/api/routes/admin.py`)
is the seam: with real users, a role check would sit beside it and raise 403
for authenticated-but-not-allowed callers. The public chat endpoint is
unauthenticated by design (a website visitor must be able to chat).

WHAT CAN FAIL: Confusing 401 with 403, checking permissions in the frontend
only (the backend must enforce), and privilege escalation through
unprotected routes (every admin route shares one dependency, so none can be
forgotten).

WHAT AN INTERVIEWER MAY ASK: authentication vs authorization, where checks
belong, role-based access control basics, why 403 never fires in this demo.

---

## 22. CORS

WHAT IT IS: Cross-Origin Resource Sharing: browser rules that block a page on
one origin from calling an API on another, unless the API opts in with
`Access-Control-Allow-*` headers.

WHY WE USED IT: The Vite dev server (localhost:5173) and the API
(localhost:8000) are different origins, so without CORS the browser blocks
every frontend request.

HOW IT WORKS IN AUTOM8R: `CORSMiddleware` in `backend/app/main.py` with
`allow_origins` from the `CORS_ORIGINS` env var (comma-separated, parsed by a
property in `backend/app/config.py`), credentials allowed, all methods and
headers. The code comment states the production rule: never `*` together
with credentials.

WHAT CAN FAIL: Origin typos (scheme and port must match exactly), credentialed
requests rejected when origins are `*`, and preflight (OPTIONS) failures on
non-simple requests.

WHAT AN INTERVIEWER MAY ASK: what CORS protects (users, not servers), what a
preflight is, why `*` plus credentials is forbidden, how you fix a CORS error.

---

## 23. Git

WHAT IT IS: Distributed version control: snapshots of your project, branches
for parallel work, and a shared history with remotes like GitHub.

WHY WE USED IT: Version control is table stakes, and the project's history is
part of the story: contract first, walking skeleton, then features with
tests.

HOW IT WORKS IN AUTOM8R: The repo root holds `backend/`, `mcp_server/`,
`frontend/`, `data/`, and `docs/`. `.gitignore` keeps `.env`, the SQLite
file, and virtualenvs out of history. Docs live in the repo
(`docs/api-contract.md` and this set) so docs and code version together.

WHAT CAN FAIL: Committing secrets (the `.env` guard), giant binary files in
history, merge conflicts from long-lived branches, and "works on my machine"
from uncommitted changes.

WHAT AN INTERVIEWER MAY ASK: clone/commit/push/pull, branching and merging,
resolving a conflict, what `.gitignore` does, what a good commit message
looks like.

---

## 24. Docker

WHAT IT IS: Containers: package an app with its dependencies into an image
that runs the same everywhere. Docker Compose runs several containers as one
system.

WHY WE USED IT: Not used in this project yet; the demo runs directly on the
host for zero-setup interviews. It belongs here because "how would you
containerize this?" is a guaranteed follow-up.

HOW IT WORKS IN AUTOM8R: It does not yet, and the answer is ready: one image
per process (backend, MCP server, frontend build), a Compose file wiring
ports 8000/8001/5173, env vars through the Compose `environment:` section,
and the SQLite file on a shared volume (or better, Postgres as a fourth
service, which removes the shared-file trick entirely).

WHAT CAN FAIL: Images built on the wrong base (use slim Python), secrets
baked into images (pass at runtime), and assuming containers fix shared-state
problems (the WAL story changes once the DB is a separate service).

WHAT AN INTERVIEWER MAY ASK: image vs container, what a Dockerfile looks
like, Compose basics, how your three processes would map to containers.

---

## 25. GCP and Cloud Run

WHAT IT IS: Google Cloud's managed container platform: push a container
image, get an HTTPS URL, scale to zero when idle, pay per request.

WHY WE USED IT: Not used; Autom8r runs locally by design. It is in these
notes because "how would you deploy this?" deserves a concrete, honest
answer.

HOW IT WORKS IN AUTOM8R: It does not yet. The deployment sketch: containerize
backend and MCP server, deploy both as Cloud Run services, move the database
to Cloud SQL (Postgres) since a shared SQLite file cannot span instances,
serve the frontend build from Cloud Storage or a static host, keep secrets in
Secret Manager, and set `CORS_ORIGINS` to the real frontend origin. The
stateless backend and the per-call MCP client were designed with exactly
this move in mind.

WHAT CAN FAIL: Cold-start latency on the chat path, the shared-SQLite
assumption breaking across instances (the real reason for Cloud SQL), and
egress costs on LLM calls.

WHAT AN INTERVIEWER MAY ASK: what Cloud Run is, scale-to-zero and cold
starts, why the database must change when you deploy, how secrets and env
vars work in cloud deployments.
