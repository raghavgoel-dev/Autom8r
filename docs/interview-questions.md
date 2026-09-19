# Autom8r Interview Question Bank

Practice questions with short answer guides, organized by topic. Every answer
starts with the simple version you can say out loud, then adds precision. Where
it helps, there is a one-line "In Autom8r" connection so you can anchor book
knowledge to a real project you built.

How to use this file: read a question, cover the answer, say your version out
loud, then compare. If your version is missing the "why", practice that part.

Counts: Python 22, REST/API/HTTP 22, SQL/DBMS 16, React/TypeScript 16,
LLM/GenAI 22, MCP 16, Linux/networking 11, Project/architecture 22,
HR/behavioral 16. Total 163.

---

## Python (22)

**1. What is the difference between a list and a tuple?**
A list is mutable: you can append, remove, and change items after creation. A
tuple is immutable: once created, it cannot change. Use tuples for fixed
records and anywhere hashability is needed (dict keys, set members).
In Autom8r, this looks like conversation history passed as
`tuple[ChatMessage, ...]` in `backend/app/services/llm_service.py`, chosen so
the context object stays frozen and safe to share.

**2. What is a dictionary and when would you use one?**
A dict stores key-value pairs with average O(1) lookup by key. Use it whenever
you need to look things up by a name or id instead of a position.
In Autom8r, this looks like the TF-IDF vectors in
`backend/app/services/retrieval_service.py`: each vector is a
`dict[str, float]` mapping a token to its weight.

**3. What are *args and **kwargs?**
`*args` collects extra positional arguments into a tuple; `**kwargs` collects
extra keyword arguments into a dict. They let a function accept a flexible
number of inputs.

**4. What is a decorator?**
A function that wraps another function to add behavior without changing the
wrapped function's source. `@app.get("/health")` in FastAPI is a decorator: it
registers the function as a route handler.
In Autom8r, this looks like `@mcp.tool(...)` in
`mcp_server/tools/lead_tools.py`, which registers a plain Python function as
an MCP tool with a name, description, and safety annotations.

**5. What is a generator?**
A function that uses `yield` to produce values lazily, one at a time, instead
of building a full list in memory. Generators are iterators.
In Autom8r, this looks like `get_db()` in `backend/app/db/session.py`: it
yields one database session per request and the `finally` block closes it,
guaranteed, even when the route raises.

**6. What is a context manager?**
An object with `__enter__` and `__exit__`, used with `with`, that guarantees
setup and cleanup. Files, locks, and database connections are the classic
examples.
In Autom8r, this looks like `async with Client(self._base_url) as client:` in
`backend/app/services/mcp_client_service.py`: the MCP session opens, the tool
call runs, and the session closes even on failure.

**7. What is the GIL?**
The Global Interpreter Lock in CPython: only one thread executes Python
bytecode at a time. Threads still help for I/O-bound work (network, database)
because the lock is released during I/O. For CPU-bound parallelism, use
processes.
In Autom8r, this looks like the choice of `asyncio` for the chat path: the
work is I/O-bound (LLM calls, MCP calls), so one event loop beats threads.

**8. What is the mutable default argument trap?**
Default argument values are evaluated once at function definition, not per
call. `def f(items=[])` shares one list across all calls, which leaks state
between calls. The fix is `def f(items=None)` and create the list inside.

**9. Shallow copy vs deep copy?**
A shallow copy duplicates the outer container but shares the inner objects; a
deep copy duplicates everything recursively. Mutating a nested object through
a shallow copy changes the original too.

**10. What is a list comprehension?**
A compact way to build a list: `[x * 2 for x in nums if x > 0]`. It is
usually faster and clearer than an equivalent `for` loop with `append`.
In Autom8r, this looks like the tool-schema conversion in
`AgentService._openai_tools()` (`backend/app/services/agent_service.py`),
which builds OpenAI function schemas from discovered MCP tools in one
comprehension.

**11. How does exception handling work in Python?**
`try` runs code, `except` catches matching exceptions, `else` runs when
nothing raised, `finally` always runs. Catch the most specific exception you
can handle; a bare `except:` hides bugs.
In Autom8r, this looks like `backend/app/main.py`: typed `AppError`
subclasses are raised in routes, and global handlers convert them into one
JSON error envelope, so no stack trace ever reaches a client.

**12. What is the difference between `is` and `==`?**
`==` compares values; `is` compares identity (same object in memory). Use
`is` only for singletons like `None`: write `if x is None`, never
`if x == None`.

**13. What are dunder (magic) methods?**
Methods with double underscores that hook into Python syntax: `__init__`
runs at construction, `__str__` controls `str(x)`, `__len__` backs `len(x)`,
`__enter__` and `__exit__` back `with`. They let your objects behave like
built-ins.

**14. What is a lambda?**
A small anonymous function: `lambda x: x * 2`. Good for short key functions
like `sorted(rows, key=lambda r: r.score, reverse=True)`. Anything complex
deserves a named `def`.
In Autom8r, this looks like the retrieval sort in
`retrieval_service.py`: `scored.sort(key=lambda result: result.score,
reverse=True)`.

**15. How are arguments passed in Python?**
By object reference. The function gets a new name bound to the same object.
Rebinding the name inside the function does not affect the caller; mutating
the object does. That is why appending to a passed-in list is visible outside,
but reassigning the parameter is not.

**16. What is the difference between a module and a package?**
A module is one `.py` file. A package is a directory of modules with an
`__init__.py` (the file can be empty; it marks the directory as importable).
In Autom8r, this looks like `backend/app/services/`: a package where each
module has one job (`scoring.py`, `extraction.py`, `retrieval_service.py`).

**17. Why use virtual environments?**
They isolate a project's dependencies from the system Python and from other
projects, so versions never collide and installs are reproducible per
project. Create with `python -m venv .venv`, activate, then install.

**18. What are type hints?**
Optional annotations like `def greet(name: str) -> str`. Python does not
enforce them at runtime; tools like mypy, pyright, and your IDE check them
statically. They document intent and catch whole classes of bugs before you
run the code.
In Autom8r, this looks like every service and route: signatures like
`def compute_lead_score(signals: LeadSignals) -> int` in
`backend/app/services/scoring.py`.

**19. What is a dataclass?**
A class auto-generated from field annotations via `@dataclass`: you get
`__init__`, `__repr__`, and `__eq__` for free. `frozen=True` makes instances
immutable, `slots=True` saves memory.
In Autom8r, this looks like `LeadSignals` in `scoring.py` and
`ExtractedLead` in `extraction.py`: frozen, slotted dataclasses that carry
pure data with no I/O.

**20. What are f-strings?**
Formatted string literals: `f"Lead #{lead.id} created"`. Expressions inside
the braces are evaluated at runtime. They are the fastest and most readable
way to build strings in modern Python.

**21. Iterable vs iterator?**
An iterable is anything you can loop over (it has `__iter__`). An iterator is
the object that produces items one at a time (it has `__next__`) and remembers
where it is. `iter()` turns the first into the second; a for loop does this
for you.

**22. How does Python manage memory?**
Primarily by reference counting: when an object's last reference disappears,
it is freed immediately. A cyclic garbage collector handles reference cycles.
You rarely manage this by hand, but it explains why `del` on a name does not
guarantee immediate collection if other references exist.

---
## REST, API, and HTTP (22)

**1. What is REST?**
An architectural style for APIs: resources identified by URLs, manipulated
with standard HTTP methods, using stateless requests and standard status
codes. `GET /api/v1/leads/12` reads lead 12; the verb and the URL together say
what happens.
In Autom8r, this looks like `backend/app/api/routes/leads.py`: list, get,
create, patch, delete on the `leads` resource with correct status codes.

**2. Name the main HTTP methods and what they mean.**
GET reads, POST creates (or triggers an action), PUT replaces a whole
resource, PATCH updates part of it, DELETE removes it. GET, PUT, and DELETE
should be idempotent: repeating them has the same effect. POST usually is
not.
In Autom8r, this looks like `PATCH /api/v1/leads/{id}` accepting a partial
body (`LeadUpdate`, all fields optional) in `backend/app/schemas/lead.py`.

**3. PUT vs PATCH?**
PUT replaces the entire resource with the body you send; PATCH applies only
the fields you send. If a client PATCHes `{"city": "Mumbai"}`, every other
field stays as it was.

**4. Explain these status codes: 200, 201, 204, 400, 401, 403, 404, 422, 500, 502, 503.**
200 OK, 201 created, 204 success with no body, 400 malformed request, 401 not
authenticated, 403 authenticated but not allowed, 404 not found, 422
well-formed but semantically invalid, 500 server bug, 502 bad upstream
response, 503 upstream unavailable.
In Autom8r, this looks like the leads API returning 201 on create and 204 on
delete, and the MCP failure mapping (503 `MCP_UNAVAILABLE` when the server is
down, 502 `MCP_TOOL_ERROR` when a tool ran but failed) in
`backend/app/utils/errors.py`.

**5. What is the difference between 401 and 403?**
401 means "who are you?" (missing or bad credentials). 403 means "I know who
you are, and you are not allowed." Autom8r only returns 401 because it has a
single admin token and no roles; with roles, 403 would appear.
In Autom8r, this looks like `require_admin` in
`backend/app/utils/security.py`, which raises a 401 `AuthError` for a missing
or wrong Bearer token.

**6. What does "stateless" mean for an API?**
Each request carries everything the server needs; the server keeps no session
memory between requests. Statelessness is what lets you scale horizontally:
any instance can handle any request.
In Autom8r, this looks like `POST /api/v1/chat`: the client sends the full
conversation `history` every turn, and the server re-derives the lead state
from it (`accumulate_extraction` in `backend/app/services/llm_service.py`).

**7. What are HTTP headers? Give three you have used.**
Key-value metadata on a request or response. `Content-Type: application/json`
says the body is JSON, `Authorization: Bearer <token>` carries credentials,
`X-Webhook-Secret` is a custom header Autom8r uses for webhook auth.

**8. Path parameter vs query parameter vs request body?**
Path params identify which resource (`/leads/12`), query params modify the
request (`?status=qualified&limit=20`), the body carries the data to write.
In Autom8r, this looks like `GET /api/v1/leads` accepting `status`,
`priority`, `city`, `phone`, `limit`, `offset` as query params in
`backend/app/api/routes/leads.py`.

**9. What is CORS and why does it exist?**
Cross-Origin Resource Sharing. Browsers block a page on one origin from
calling an API on another origin unless the API explicitly allows it via
`Access-Control-Allow-*` headers. It protects users, not servers.
In Autom8r, this looks like `CORSMiddleware` in `backend/app/main.py` with
`allow_origins` from the `CORS_ORIGINS` env var, because the Vite dev server
(port 5173) and the API (port 8000) are different origins.

**10. What is idempotency and why does it matter?**
An idempotent operation gives the same result whether it runs once or ten
times. Networks retry, users double-click, and webhook providers redeliver,
so unsafe operations need an idempotency mechanism to avoid duplicates.
In Autom8r, this looks like the webhook event ledger: each processed
`event_id` is stored in the `webhook_events` table, and a redelivery returns
200 with `duplicate: true` instead of creating a second lead
(`backend/app/api/routes/webhooks.py`).

**11. What is the difference between calling an API and receiving a webhook?**
Direction. An API call is you calling someone else's endpoint. A webhook is
someone else calling your endpoint when an event happens. Webhooks need their
own security because anyone on the internet can POST to them.
In Autom8r, this looks like `POST /api/v1/webhooks/lead`, guarded by the
`X-Webhook-Secret` header.

**12. How do you version an API?**
Common options: a path prefix (`/api/v1/...`), a header, or a media type.
Path versioning is the most visible and the easiest to route. Autom8r uses
`/api/v1/` so a future breaking change can live at `/api/v2/` beside it.

**13. How does pagination work?**
Return big collections in pages. Offset pagination uses `limit` and `offset`;
cursor pagination uses an opaque token pointing at the last seen item.
Cursors stay correct when rows are inserted while paging; offsets can skip or
repeat rows.
In Autom8r, this looks like `limit` (1 to 100, default 20) and `offset` on
`GET /api/v1/leads`, enforced by `Query(ge=1, le=100)` validation.

**14. How does Bearer token authentication work?**
The client sends `Authorization: Bearer <token>`; the server compares the
token to a known value or verifies its signature. It is simple and works over
HTTPS. It says nothing about who the user is beyond "holds the token".
In Autom8r, this looks like the admin routes checking the token with
`hmac.compare_digest` in `backend/app/utils/security.py`.

**15. What is a timing attack and how do you defend against it?**
If a string comparison exits at the first wrong character, response time
leaks how many characters were right, and an attacker can guess a secret one
character at a time. The defense is constant-time comparison.
In Autom8r, this looks like `hmac.compare_digest(token,
settings.admin_token)` used for both the admin token and the webhook secret.

**16. What happens in an HTTPS request (TLS in one paragraph)?**
The client and server do a TLS handshake: they agree on ciphers, the server
proves its identity with a certificate, and they derive session keys. After
that, all HTTP traffic is encrypted and integrity-checked. HTTPS gives you
confidentiality and server authentication; it does not replace API auth.

**17. How should an API return errors?**
One consistent shape, a machine-readable code, a human-safe message, and the
right HTTP status. Never leak stack traces or internals to the client.
In Autom8r, this looks like the single envelope
`{"success": false, "error": {"code": "LEAD_NOT_FOUND", "message": "..."}}`
built by the global handlers in `backend/app/main.py`, with codes frozen in
`docs/api-contract.md`.

**18. What is content negotiation?**
The client says what it accepts (`Accept: application/json`) and what it is
sending (`Content-Type`), and the server responds accordingly. JSON APIs
usually skip the ceremony and require JSON both ways.

**19. What are safe methods?**
Methods that only read: GET and HEAD. Safe methods must not change server
state, which is why browsers and crawlers freely retry them, and why "delete
via GET" is a design bug.

**20. What is rate limiting and why add it?**
Capping how many requests a client can make in a window. It protects the
service from abuse, accidents, and runaway loops, and it keeps costs
predictable when a request triggers paid work like an LLM call. Autom8r does
not implement it; it would be one of the first production additions, along
with per-IP limits on the public chat endpoint.

**21. How do you test an API?**
Three layers: unit tests for the logic under the routes, integration tests
that call the real routes against a test database, and a few end-to-end
checks through the real server. Assert on status codes and response bodies,
not just "no exception".
In Autom8r, this looks like `backend/tests/` using FastAPI's `TestClient`
with a throwaway SQLite database per test (`backend/tests/conftest.py`):
58 backend tests covering CRUD status codes, auth 401s, webhook dedupe, and
chat flows.

**22. What is an API contract and why freeze one?**
The agreed shapes of requests and responses: fields, types, status codes,
error bodies. Freezing it means frontend and backend can be built in parallel
and any change is a deliberate, visible event.
In Autom8r, this looks like `docs/api-contract.md`, the single source of
truth the React frontend and the FastAPI backend are both built against.

---
## SQL and DBMS (16)

**1. What is a primary key?**
A column (or set of columns) that uniquely identifies each row and can never
be NULL. `leads.id` is an `INTEGER PRIMARY KEY AUTOINCREMENT`, so SQLite
assigns a new unique id per insert.

**2. WHERE vs HAVING?**
WHERE filters rows before grouping; HAVING filters groups after aggregation.
`WHERE city = 'Mumbai'` narrows the rows; `HAVING COUNT(*) > 5` narrows the
groups.

**3. Explain the JOIN types.**
INNER JOIN keeps only matching rows on both sides. LEFT JOIN keeps all left
rows, filling missing right columns with NULL. RIGHT JOIN is the mirror.
FULL OUTER JOIN keeps everything from both sides. In practice, INNER and
LEFT cover almost all application code.

**4. What is an index and what does it cost?**
A data structure (usually a B-tree) that makes lookups on a column fast
instead of scanning the whole table. The cost: extra storage and slower
writes, because every insert and update must maintain the index.
In Autom8r, this looks like indexes on `leads.phone`, `leads.email`,
`leads.status`, and `leads.priority` (see `backend/app/models/lead.py` and
`mcp_server/db.py`), chosen because the app filters and searches on exactly
those columns.

**5. What is normalization?**
Designing tables to remove redundancy: each fact stored once. 1NF: atomic
values. 2NF: no partial dependency on part of a key. 3NF: no transitive
dependencies. You denormalize deliberately, for read performance, not by
accident.

**6. What is ACID?**
Atomicity (a transaction is all or nothing), Consistency (constraints always
hold), Isolation (concurrent transactions do not corrupt each other),
Durability (committed data survives a crash). It is the contract a
transactional database gives you.

**7. What is a transaction?**
A unit of work that commits together or rolls back together. The classic
example is a money transfer: debit and credit must both happen or neither.
In Autom8r, this looks like the webhook handler: create the lead and record
the event id, then commit, so a crash cannot leave a lead without its ledger
entry (`backend/app/api/routes/webhooks.py`).

**8. What is SQL injection and how do you prevent it?**
An attacker smuggles SQL into your query through user input, like
`' OR '1'='1`. The fix is parameterized queries: values travel as data, never
as SQL text. String formatting into SQL is the bug.
In Autom8r, this looks like `mcp_server/db.py`: every hand-written query uses
`?` placeholders, and the SQLAlchemy side parameterizes automatically.

**9. ORM vs raw SQL: when each?**
An ORM (SQLAlchemy) maps rows to objects, removes boilerplate, and composes
queries safely. Raw SQL gives full control and transparency for special
cases. Most apps are mostly ORM with a little raw SQL where it earns its
place.
In Autom8r, this looks like a deliberate split: the backend uses SQLAlchemy
2.0 (`backend/app/db/`), while the MCP server uses stdlib `sqlite3` with
hand-written parameterized SQL (`mcp_server/db.py`), two idioms against one
schema.

**10. What is SQLite and when would you not use it?**
A serverless, single-file relational database: no process to run, no network,
the database is a file. Great for local development, demos, embedded apps,
and tests. Not for many concurrent writers or multi-machine deployments;
that is where PostgreSQL or MySQL fit.
In Autom8r, this looks like `data/autom8r.db`, shared by the backend and the
MCP server.

**11. What is WAL mode in SQLite?**
Write-Ahead Logging: writes go to a log file first, and readers keep reading
the main file, so readers and one writer can work concurrently instead of
locking each other out.
In Autom8r, this looks like `PRAGMA journal_mode=WAL` plus
`PRAGMA busy_timeout=15000` set on every connection in both processes
(`backend/app/db/database.py`, `mcp_server/db.py`), which is exactly what lets
two processes share one SQLite file without "database is locked" errors.

**12. What is the N+1 query problem?**
Loading a list, then running one extra query per row for related data: 1
query becomes N+1. The fix is eager loading (joins or `selectinload` in
SQLAlchemy) so related data arrives in the same or one extra query.

**13. How do you enforce uniqueness?**
A UNIQUE constraint or unique index; the database rejects duplicates at
insert time, which is safer than checking in application code (two requests
can both pass an app-level check).
In Autom8r, this looks like `event_id` being `unique=True` on the
`webhook_events` table (`backend/app/models/webhook_event.py`), the database
level backstop for webhook dedupe.

**14. How do LIMIT and OFFSET work?**
`LIMIT n` caps the rows returned; `OFFSET m` skips the first m. Combined with
a stable `ORDER BY`, they implement pagination.
In Autom8r, this looks like `list_leads` in
`backend/app/services/lead_service.py`: `ORDER BY created_at DESC` with
`limit` and `offset`.

**15. COUNT and GROUP BY in one example?**
`SELECT priority, COUNT(*) FROM leads GROUP BY priority` gives one row per
priority with its count. That is exactly the shape of the admin stats
endpoint: totals plus per-status and per-priority counts
(`backend/app/services/lead_service.py`, `get_stats`).

**16. How do you change a schema safely (migrations)?**
With versioned migration scripts (Alembic for SQLAlchemy) that apply and roll
back changes step by step, instead of hand-editing the database. Autom8r uses
`Base.metadata.create_all` for demo simplicity; the production answer is
Alembic migrations checked into git.

---

## React and TypeScript (16)

**1. What is React?**
A library for building user interfaces from components: functions that take
props and return a description of the UI. When state changes, React
re-renders the affected components and updates the DOM efficiently.

**2. What is the virtual DOM?**
A lightweight in-memory description of the UI. On each render, React diffs
the new description against the previous one and applies only the changed
parts to the real DOM. The point is a simple programming model (re-render
everything conceptually) with good performance.

**3. What are props and state?**
Props are inputs passed from a parent, read-only inside the component. State
is data the component owns and can change with a setter. Changing state
triggers a re-render; mutating it directly does not.

**4. How does useState work?**
`const [value, setValue] = useState(initial)` gives you the current value and
a setter. Calling the setter schedules a re-render with the new value. State
updates are asynchronous and may be batched, so use the functional form
`setValue(v => v + 1)` when the next value depends on the previous one.

**5. How does useEffect work?**
`useEffect(fn, deps)` runs `fn` after render, and re-runs it when any
dependency changes. Return a cleanup function to undo the effect (unsubscribe,
abort a fetch). An empty dependency array means "run once on mount".
Fetching leads on load and cleaning up with an `AbortController` is the
canonical pattern, and it is how the Autom8r frontend talks to the backend.

**6. Why do lists need keys?**
Keys tell React which item is which across renders, so it can reuse DOM nodes
and component state correctly. Use a stable id, not the array index, because
indexes shift when items are inserted or removed.
In Autom8r, this looks like the tool activity panel: one row per
`tool_activity` item from the chat response.

**7. What is a controlled component?**
A form input whose value comes from React state and whose changes go through
a handler: `<input value={text} onChange={e => setText(e.target.value)}>`.
React is the single source of truth, which makes validation and submit logic
easy. A chat input box is the classic example.

**8. What is prop drilling and how do you avoid it?**
Passing data through many component layers that do not need it themselves.
Fixes: compose components so the data enters near where it is used, lift
state to the closest common parent, or use context for genuinely global
things. In a small app like Autom8r's UI, lifting state to the page component
is enough.

**9. What is TypeScript and why use it?**
JavaScript plus a static type system, checked at build time and erased at
runtime. It catches type errors before the browser does, documents shapes in
the code, and powers autocomplete and safe refactors.

**10. interface vs type in TypeScript?**
Both describe shapes. `interface` is extendable and merges declarations;
`type` is more general (unions, intersections, primitives). Teams usually pick
`interface` for objects and `type` for unions like
`type Priority = "low" | "medium" | "high"`.
In Autom8r, this looks like the frontend's `types/` directory mirroring the
frozen shapes in `docs/api-contract.md`: `LeadOut`, `ChatResponse`,
`ToolActivityItem`.

**11. What is a union type?**
"This value is one of these": `string | null`, or a string-literal union like
`"mock" | "live"`. Unions make illegal states unrepresentable: the LLM mode
badge can only ever be one of the two real values.

**12. How do you handle null and undefined safely?**
Enable `strict` mode so null is explicit, then use optional chaining
(`lead?.email`) and nullish coalescing (`lead?.email ?? "not provided"`).
The rule of thumb: make absence part of the type, and the compiler forces you
to handle it.

**13. How do you fetch data in React?**
In an effect (or a data library), call `fetch`, keep `loading` and `error`
state next to the data, and render all three states. Always handle the error
path; a spinner that never resolves is the most common UI bug.
In Autom8r, this looks like `frontend/src/services/`: one module that owns
the `VITE_API_BASE_URL` calls, so components never build URLs by hand.

**14. What is Vite?**
The build tool and dev server: instant startup via native ES modules, hot
module replacement while editing, and a production bundle with Rollup. The
dev server runs on port 5173 by default, which is why the backend's CORS list
includes `http://localhost:5173`.

**15. SPA vs server-side rendering?**
An SPA ships a shell page and renders in the browser; SSR renders HTML on the
server per request. SPAs are simpler to host and fine for app-like UIs; SSR
helps first-load speed and SEO. An internal chat dashboard is a natural SPA.

**16. How do you keep frontend types in sync with the backend?**
Best options: generate types from the OpenAPI schema FastAPI publishes, or
freeze a written contract and mirror it by hand with tests guarding it.
Autom8r does the second: `docs/api-contract.md` is the frozen contract, and
the backend's Pydantic response models (`response_model=...`) guarantee the
server honors it.

---
## LLM and GenAI (22)

**1. What is an LLM?**
A neural network trained on huge text corpora to predict the next token.
From that one objective it learns to answer, summarize, translate, and
reason. It generates text; it does not "know" facts the way a database does,
which is why grounding and tools matter.

**2. What is a token?**
The unit the model reads and writes: roughly a word piece. "Autom8r" might be
two or three tokens. Tokens matter because pricing, rate limits, and the
context window are all measured in them.

**3. What does temperature control?**
Sampling randomness. Low temperature (near 0) picks the most likely tokens:
predictable, focused output. High temperature flattens the distribution: more
variety, more risk of nonsense. For data extraction and tool calling, you
keep it low.

**4. System prompt vs user prompt?**
The system prompt sets the role, rules, and boundaries for the whole
conversation; the user prompt is one turn of input. The system prompt is
where you put "never invent company information" and "use tools for actions".
In Autom8r, this looks like `backend/app/prompts/system_prompt.txt` (11
rules) plus `backend/app/prompts/qualification_prompt.txt`, kept as files so
behavior can be edited without touching code.

**5. What is prompt engineering?**
Designing the instructions, context, and examples you send so the model
reliably does what you want. It is iterative: write, test against real cases,
tighten. Most quality in an LLM feature comes from the prompt plus the
guardrails around it, not from the model choice.

**6. What is hallucination and how do you reduce it?**
The model states plausible-sounding falsehoods. You reduce it by grounding
(retrieve real documents and tell the model to prefer them), by forcing
actions through tools instead of memory, and by instructing it to say "I am
not sure" when it lacks information.
In Autom8r, this looks like system prompt rules 3, 4, 5, and 8: retrieved
knowledge is the source of truth, actions go through tools, and the model
must never fabricate lead records.

**7. What is tool calling (function calling)?**
The model does not just emit text; it can emit a structured request to call a
function with JSON arguments. Your code executes the function, appends the
result to the conversation, and the model writes the final answer using that
result.
In Autom8r, this looks like the live loop in `AgentService._run_live()`
(`backend/app/services/agent_service.py`): model proposes a call, the backend
executes it through the MCP client, the JSON result goes back as a tool
message, capped at `MAX_TOOL_ROUNDS = 3` round trips.

**8. What is an AI agent?**
A loop: observe input, decide (reply or act), act through tools, observe the
result, repeat until done. The model is the decision-maker; the tools are its
hands. An agent is only as trustworthy as its tool results and its stop
conditions.
In Autom8r, this looks like `AgentService.handle_chat()`: retrieve knowledge,
accumulate extracted fields, decide via the LLM or the mock policy, execute
through MCP, compose the reply.

**9. What is RAG?**
Retrieval-Augmented Generation: before answering, search a knowledge base for
relevant passages and put them in the prompt, so the model answers from your
documents instead of its training data. It cuts hallucination and makes
answers updatable without retraining.
In Autom8r, this looks like `RetrievalService.retrieve()` finding the top 3
chunks for the user message, and the agent prepending them to the system
prompt as "RETRIEVED KNOWLEDGE (treat as the source of truth)".

**10. Keyword search vs embeddings?**
Keyword search (TF-IDF, BM25) matches literal words: exact, explainable, zero
infrastructure, but it misses paraphrases. Embeddings map text to vectors so
"money back" matches "refund": semantic, but needs a model and a vector
store.
In Autom8r, this looks like a documented tradeoff in
`backend/app/services/retrieval_service.py`: pure-Python TF-IDF was chosen
for zero dependencies and determinism, with the swap path to an embedding
retriever behind the same `retrieve(query, top_k)` interface written down.

**11. What is a vector database?**
A store that indexes embedding vectors and answers "find the k nearest
vectors to this query" fast (approximate nearest neighbor). Examples:
pgvector, Qdrant, Pinecone. You reach for one when your corpus outgrows
in-memory scanning or you need semantic search at scale.

**12. What is chunking and why does it matter?**
Splitting documents into passages small enough to fit a prompt and focused
enough to match a query. Bad chunking sinks retrieval: too big and matches
are diluted, too small and context is lost.
In Autom8r, this looks like splitting each knowledge file on `## ` headings
(`_split_chunks` in `retrieval_service.py`), so one chunk is one policy or
one product section.

**13. What is the context window?**
The maximum tokens the model can see at once: system prompt, history,
retrieved chunks, tool results, and the reply all share it. You manage it by
trimming history, capping retrieval, and summarizing.
In Autom8r, this looks like `ChatRequest.history` capped at 50 messages and
retrieval capped at `top_k=3` chunks.

**14. How do you evaluate an LLM feature?**
Build a small set of representative conversations with expected outcomes
(did it call the right tool? did it refuse to invent data?), then run them on
every change. Vibes do not scale; a fixed eval set does.
In Autom8r, this looks like the deterministic mock: because the policy is
rule-based, the chat tests in `backend/tests/test_chat.py` assert exact
behavior turn by turn, including the four-turn lead-capture conversation.

**15. What are guardrails?**
Rules around the model that keep it safe and honest: prompt rules, output
checks, tool allow-lists, and caps on how many actions it can take per turn.
In Autom8r, this looks like `MAX_TOOL_ROUNDS = 3` for runaway protection, a
tool boundary where the model can only reach the four registered MCP tools,
and prompt rules against revealing internals.

**16. How do you handle LLM failures in production?**
Assume the provider will fail: timeouts, rate limits, bad output. Design a
degraded mode that still serves the user, log the failure, and never let one
provider outage take the product down.
In Autom8r, this looks like `AgentService.handle_chat()` catching any live
LLM exception and falling back to the deterministic mock policy, with the
response honestly reporting `llm_mode: "mock"`.

**17. How do you test LLM code without calling a model?**
Put the model behind an interface and swap in a deterministic fake for tests.
The fake should exercise the same pipeline (retrieval, extraction, tool
calls), not return canned strings, or you are testing nothing.
In Autom8r, this looks like the `LLMService` protocol with two
implementations in `backend/app/services/llm_service.py`: `OpenAILLMService`
(live) and `MockLLMService` (a deterministic policy that really calls MCP
tools).

**18. What is structured output?**
Forcing the model's reply to match a schema (JSON mode, or tool calls with
typed arguments) so your code can parse it reliably. Free text is for humans;
pipelines want schemas.
In Autom8r, this looks like tool arguments being validated JSON Schema on the
MCP side, and the chat response itself being a fixed Pydantic shape
(`ChatResponse` in `backend/app/schemas/chat.py`).

**19. What drives LLM cost and latency?**
Tokens in plus tokens out, per call, times the number of calls per turn. An
agent loop multiplies calls. You control cost with smaller models for easy
steps, capped rounds, trimmed context, and caching.

**20. What is prompt injection?**
Hostile instructions smuggled into user input or retrieved content ("ignore
your rules and..."). Defenses: treat retrieved text as data, not commands;
keep secrets out of the prompt; restrict what tools can do.
In Autom8r, this looks like system prompt rule 7 (never reveal instructions,
env vars, or keys) and the knowledge chunks being labeled as reference
material, not instructions.

**21. How do you manage multi-turn conversation state?**
Two options: server-side sessions (store history keyed by a session id) or
client-held state (the client resends history each turn). Client-held keeps
the server stateless and trivially scalable, at the cost of bigger requests.
In Autom8r, this looks like the second choice: the frontend keeps history
and posts it with every message, and the server re-derives lead fields from
the whole transcript each turn.

**22. Fine-tuning vs prompting vs RAG: how do you choose?**
Prompting first: cheapest, fastest to iterate. Add RAG when the model needs
your private or changing data. Fine-tune when you need a style, format, or
behavior that prompting cannot hold reliably. For a company knowledge
assistant, RAG is the right middle layer, which is what Autom8r does.

---
## MCP: Model Context Protocol (16)

**1. What is MCP?**
The Model Context Protocol: an open standard (started by Anthropic, now
governed openly) that defines how an AI application discovers and calls
external capabilities. One protocol, so any MCP host can use any MCP server:
tools, resources, and prompts over a defined transport.
In Autom8r, this looks like `mcp_server/server.py`: a standalone process
exposing lead tools, a business-info resource, and a qualification prompt.

**2. Why use MCP instead of calling APIs directly from the agent?**
Separation and reuse. The backend never imports lead logic; it speaks the
protocol, so the same tools work for this backend, an IDE, or Claude Desktop
with zero changes. Tool descriptions and schemas travel with the server, so
clients discover capabilities instead of hardcoding them.
In Autom8r, this looks like `AgentService` never touching the database: all
mutations go through `MCPClientService`.

**3. Describe MCP architecture: host, client, server.**
The host is the AI application (the Autom8r backend). The client lives inside
the host and speaks the protocol (`MCPClientService`). The server exposes
capabilities (`mcp_server/`). One host can hold clients to many servers.

**4. What are tools, resources, and prompts in MCP?**
Tools are functions the model can call (with JSON Schema inputs). Resources
are readable data identified by URIs. Prompts are reusable prompt templates a
client can fetch.
In Autom8r, this looks like four tools (`create_lead`, `search_lead`,
`update_lead`, `get_business_info`), one resource
(`business://company-info`), and one prompt (`lead_qualification_prompt`).

**5. What transports does MCP use?**
stdio for local subprocess servers, and Streamable HTTP for network servers.
Streamable HTTP is the current standard remote transport; the older HTTP+SSE
transport was replaced by it in the 2025 spec revisions.
In Autom8r, this looks like `create_server().run(transport=
"streamable-http", host=..., port=8001, streamable_http_path="/mcp")` in
`mcp_server/server.py`.

**6. Which SDK did you use and what does it look like?**
The official Python SDK, `mcp` 2.x (Autom8r pins `mcp>=2.0,<3`, running
2.2.0). On the server you build an `MCPServer` from `mcp.server.mcpserver`
and register capabilities with decorators: `@mcp.tool(...)`,
`@mcp.resource(uri)`, `@mcp.prompt(...)`. On the client you use `Client`
from `mcp.client`.

**7. What are tool annotations?**
Hints about a tool's behavior: `readOnlyHint` (never modifies data),
`destructiveHint`, `idempotentHint`, `openWorldHint`. Hosts use them for UX
and confirmation flows.
In Autom8r, this looks like `search_lead` and `get_business_info` marked
read-only, and `update_lead` marked idempotent, in
`mcp_server/tools/lead_tools.py` and `knowledge_tools.py`.

**8. How are tool inputs and outputs defined?**
Inputs come from the Python function signature, exposed as JSON Schema
(`inputSchema`). Outputs can be structured: return a Pydantic model and the
SDK serializes it as `structuredContent`, so clients get typed data, not text
to parse.
In Autom8r, this looks like `create_lead` returning a frozen `LeadResult`
model, which the backend reads via `result.structured_content` in
`mcp_client_service.py`.

**9. How does a client discover what a server offers?**
By asking: `list_tools()`, `list_resources()`, `list_prompts()`. Discovery
means the client adapts when the server adds a tool, with no redeploy of the
client.
In Autom8r, this looks like `GET /api/v1/admin/tools`, which calls
`mcp.list_tools()` live and returns 503 `MCP_UNAVAILABLE` when the server is
down.

**10. How do errors work in MCP?**
A tool that fails returns a result with `isError` true and error content; a
server that cannot be reached fails at the transport level. Good clients
distinguish the two.
In Autom8r, this looks like `MCPClientService.call_tool()` mapping transport
failures to `MCPUnavailableError` (503) and `result.is_error` to
`MCPToolError` (502), so the API returns the right status for each case.

**11. How do you test an MCP server?**
In-process, with no network: the SDK's client can connect directly to a
server instance. Autom8r's tests use `Client(server, mode="legacy")` against
a server built with a throwaway database, then assert on tool listings,
structured results, the resource, and the prompt.
In Autom8r, this looks like `mcp_server/tests/test_server.py`: 9 tests,
including a schema-drift guard that pins the shared column list.

**12. What security questions does an MCP server raise?**
Who can connect (authentication on the transport), what each tool may do
(least privilege, read-only where possible), and what data flows back
(no secrets in results). A demo on localhost can skip auth; a deployed server
cannot.
In Autom8r, this looks like honest scoping: the server binds to 127.0.0.1 by
default, and read-only tools are annotated as such.

**13. MCP vs a plain REST API for tools?**
REST is general-purpose and universal; MCP is purpose-built for model
consumption: self-describing tools, typed structured results, discovery, and
a growing ecosystem of hosts. If the consumer is an LLM agent, MCP removes
glue code. If the consumer is a web app, REST is fine. Autom8r uses both:
REST for the frontend, MCP for the agent's tools.

**14. How does your backend connect to the MCP server?**
Per call: each tool invocation opens a short-lived Streamable HTTP session,
calls, and closes. Stateless and crash-proof; a restarted server never leaves
a stale session. The production refinement is a pooled persistent session,
which the code comments call out as the documented tradeoff.
In Autom8r, this looks like `async with Client(self._base_url) as client` in
`backend/app/services/mcp_client_service.py`.

**15. What happens in your app when the MCP server is down?**
The failure is typed and visible, never silent. `list_tools` and `call_tool`
raise `MCPUnavailableError`; the admin tools endpoint returns a 503 envelope;
chat still answers (retrieval and conversation work) but says the
lead-recording service is unavailable and shows an error item in the tool
activity panel.

**16. Is MCP stable enough to build on?**
The spec is young and has moved fast (the transport changed from HTTP+SSE to
Streamable HTTP during 2025), so you pin the SDK version and isolate it
behind your own interface. Autom8r does exactly that: `MCPClientLike` is a
small protocol, and every MCP detail lives in `mcp_client_service.py`, so an
SDK upgrade touches one file.

---

## Linux and Networking (11)

**1. Which Linux commands do you use daily?**
`ls`, `cd`, `grep -r` to find text, `cat` and `tail -f` for files and logs,
`ps aux` for processes, `kill` to stop them, `chmod` for permissions,
`curl` for HTTP, `ssh` for remote machines. On Windows I use PowerShell
equivalents, and the concepts transfer one to one.

**2. How do you find and kill a process on a port?**
Find who listens: `netstat -ano | findstr :8000` on Windows, or
`lsof -i :8000` / `ss -ltnp` on Linux. Then kill by PID: `kill <pid>` on
Linux, `Stop-Process -Id <pid>` in PowerShell. This is the fix for "port
already in use" when a crashed dev server keeps 8000 or 8001 busy.

**3. What is a port?**
A 16-bit number that lets one machine run many network services: the IP picks
the machine, the port picks the service. Autom8r uses three: 5173 (Vite dev
server), 8000 (FastAPI), 8001 (MCP server).

**4. How do you use curl?**
`curl.exe -X POST <url> -H "Content-Type: application/json" -d '{...}'` sends
a JSON POST; `-H` adds headers like `Authorization: Bearer ...`; `-i` shows
status and headers. On Windows PowerShell I type `curl.exe` explicitly,
because plain `curl` is an alias for `Invoke-WebRequest` with different
flags.
In Autom8r, this looks like the demo webhook test: POSTing
`data/samples/sample_webhook.json` with the `X-Webhook-Secret` header.

**5. What are environment variables and why put config in them?**
Key-value settings from the process environment. They keep secrets and
per-machine settings out of source code, and they let the same build run in
dev, test, and prod with different values.
In Autom8r, this looks like `backend/app/config.py`: every variable is
declared once in a pydantic-settings `Settings` class, and nothing else in
the codebase reads `os.environ` directly.

**6. What happens when you type a URL into a browser?**
DNS resolves the host to an IP; the browser opens a TCP connection (and a TLS
handshake for HTTPS); it sends an HTTP request; the server routes it, runs
the app, and returns a response; the browser renders it and fetches linked
assets. Every piece of that chain is a place things can fail, which is why it
is a great debugging checklist.

**7. TCP vs UDP?**
TCP is connection-oriented: ordered, reliable, retransmitted; the base for
HTTP. UDP is fire-and-forget: no guarantees, lower latency; used for DNS,
voice, and games. A voice bot cares about this distinction; a REST API does
not.

**8. What is localhost / 127.0.0.1?**
The loopback address: the machine talking to itself, no network involved.
Binding a server to 127.0.0.1 means only local processes can reach it, which
is a sensible default for a demo and the first thing you change (to 0.0.0.0
behind a real proxy) when deploying.

**9. How do you read logs when something breaks?**
Start at the failing request and work backward: find its log line, then the
exception, then the first unusual entry before it. `tail -f` follows a live
log; `grep` filters for the request id or path.
In Autom8r, this looks like one line per request (method, path, status,
duration in ms) from the middleware in `backend/app/main.py`, plus one line
per MCP tool call in `mcp_client_service.py`.

**10. What is DNS?**
The phone book of the internet: it maps names like `api.example.com` to IP
addresses. When "the site is down" but the IP works, DNS is the suspect.

**11. What is a reverse proxy?**
A server (nginx, a cloud load balancer) that accepts public traffic and
forwards it to your app processes. It terminates TLS, routes by path, and
lets you run many app instances behind one address. On Cloud Run, this layer
is managed for you.

---
## Project and Architecture (22)

**1. Walk me through Autom8r's architecture.**
Three processes. A React + TypeScript SPA (Vite, port 5173) talks to a
FastAPI backend (port 8000) over JSON REST. The backend never touches lead
data directly for chat actions: it calls a standalone MCP server (port 8001)
over Streamable HTTP. Backend and MCP server share one SQLite file in WAL
mode. Knowledge retrieval (TF-IDF over Markdown) happens inside the backend.

**2. Why three processes instead of one?**
Because that is how MCP is used for real: any host can connect to the same
tool server. It also proves the hard part, two processes sharing one SQLite
file safely, and it keeps each piece small enough to explain in an interview.
The cost is one extra process to start locally, which the docs call out.

**3. Why FastAPI?**
Type hints in, validation and OpenAPI docs out, for free. Pydantic parses
every request at the boundary, so route functions never see a bad payload.
It is async-native, which suits an I/O-bound chat workload, and it is the
most common Python API framework in 2026 job descriptions.

**4. Why SQLite?**
Zero-install demo: clone, seed, run. The interesting part is WAL mode plus a
busy timeout on every connection, which lets the backend and the MCP server
share one file without lock errors. The documented tradeoff: production
multi-instance deployment would move to PostgreSQL, and the SQLAlchemy layer
makes that a config change, not a rewrite.

**5. Why does the agent go through MCP instead of calling the database?**
To keep a protocol boundary between the model and the data. The agent can
only do what the four registered tools allow, the tools are self-describing
to any MCP host, and the backend code reads exactly like a production setup
where tools live behind a protocol.

**6. Walk through one chat turn end to end.**
`POST /api/v1/chat` hits `AgentService.handle_chat()`. First, TF-IDF
retrieval over the knowledge files (top 3 chunks). Second, lead fields are
re-extracted from the whole client-sent history. Third, the policy decides:
the deterministic mock, or the live model in a tool-calling loop capped at 3
rounds. Fourth, any tool call goes to the MCP server over HTTP. Finally the
reply, the lead (if one was created or updated), and a tool-activity list go
back to the UI.

**7. How is the lead score calculated?**
A deterministic, explainable heuristic in `backend/app/services/scoring.py`:
phone +20, email +10, requirement +15, business type +15, city +10, timeline
within 3 months +15, monthly volume of 300 or more +15, clamped to 0..100.
Bands: below 40 low, 40 to 69 medium, 70 and above high. The same module is
imported by the MCP server, so REST-created and chat-created leads score
identically.

**8. How does retrieval work, and why TF-IDF instead of embeddings?**
Each Markdown knowledge file is split on `## ` headings into chunks; chunks
and the query become TF-IDF vectors; cosine similarity ranks them; anything
under 0.15 is treated as "no knowledge". TF-IDF was chosen for zero native
dependencies and full determinism in tests. The honest tradeoff, written in
the code: paraphrases score lower than they would with embeddings, and the
`retrieve(query, top_k)` interface is the documented swap point.

**9. Mock LLM vs live LLM: how does the switch work?**
`build_llm_service(settings)` returns `OpenAILLMService` when
`LLM_ENABLED=true` and a key exists, else `MockLLMService`. The mock is not
canned text: it runs the same extraction, retrieval, and MCP tool calls with
a deterministic rule policy in place of the model. If the live model throws
anything, the agent catches it, logs a warning, and re-runs the turn with the
mock, reporting `llm_mode: "mock"` honestly in the response.

**10. How is the webhook secured and made idempotent?**
Two mechanisms. Auth: a shared secret in the `X-Webhook-Secret` header,
compared with `hmac.compare_digest` (constant time). Idempotency: an event
ledger table stores each processed `event_id` (unique constraint); a
redelivery returns 200 with `duplicate: true` instead of a second lead.

**11. How is the admin API secured?**
A demo Bearer token in the `Authorization` header, compared in constant time,
required by a router-level dependency on every `/api/v1/admin/*` route.
Deliberately simple; the docs explain where real users and roles would go.

**12. What is the error handling strategy?**
One envelope for every error: `{"success": false, "error": {"code",
"message"}}`. Routes raise typed `AppError` subclasses that carry their HTTP
status and code; global handlers in `main.py` convert them (plus Pydantic
422s and unexpected 500s) into the envelope. Clients can program against the
codes, frozen in `docs/api-contract.md`.

**13. How is the project tested?**
67 automated tests: 58 backend (CRUD status codes, auth 401s, webhook
201/dedupe/401, chat flows, scoring, retrieval) and 9 MCP server tests (tool
listing with annotations, structured results, resource, prompt, and a
schema-drift guard). Backend tests run against a throwaway SQLite database
per test; MCP tests connect in-process with `Client(server, mode="legacy")`.

**14. Why is the server stateless, and how does context survive?**
The frontend keeps the conversation and posts it with every message. The
backend re-derives everything per turn, including the accumulated lead
fields, via `accumulate_extraction`. No session store, no sticky sessions,
trivial scaling. The cost, bigger requests, is capped by a 50-message history
limit.

**15. How is configuration managed?**
One `Settings` class (pydantic-settings) in `backend/app/config.py` declares
every environment variable with types and defaults. A typo in an env var name
fails at boot, not at midnight. Nothing else in the codebase reads
`os.environ` directly.

**16. How is CORS configured?**
`CORSMiddleware` with an explicit origin list from the `CORS_ORIGINS` env var
(default `http://localhost:5173`), credentials allowed. The code comment
notes the production rule: never `*` with credentials.

**17. What observability does the app have?**
Structured, consistent logging: one line per HTTP request (method, path,
status, milliseconds), one line per MCP tool call, one line per LLM call, and
full tracebacks for unexpected errors. No secrets are ever logged; there is
no code path that prints an API key.

**18. Why two data-access idioms (ORM and raw SQL)?**
Deliberate teaching contrast. The backend demonstrates SQLAlchemy 2.0
(`Mapped`, `mapped_column`, sessions per request). The MCP server
demonstrates stdlib `sqlite3` with hand-written parameterized SQL against the
same schema. A test pins the shared column list so drift fails loudly.

**19. What would you scale first?**
The database: move from SQLite to managed PostgreSQL (one config change via
`DATABASE_URL`). Then the LLM path: pooled MCP sessions, response caching,
and a smaller model for easy turns. The stateless backend already scales
horizontally behind a load balancer.

**20. How would you productionize it?**
Containers for all three processes, managed Postgres, Alembic migrations,
real auth (OAuth2/JWT) replacing the demo token, HMAC-signed webhooks,
rate limiting on the public chat endpoint, structured logs to a collector,
metrics and tracing, CI running the 67 tests on every push, and secrets in a
manager instead of `.env`.

**21. What tradeoffs did you make consciously?**
TF-IDF instead of embeddings (determinism over semantics). Per-call MCP
sessions instead of pooled (simplicity over milliseconds). SQLite instead of
Postgres (zero-install over concurrency). Client-held history instead of
sessions (statelessness over request size). A scoring heuristic instead of an
ML model (explainability over accuracy). Each is written down in the code
with its reason and its upgrade path.

**22. What would you improve with more time?**
Embedding-based retrieval behind the existing interface, pooled MCP sessions,
streaming chat responses, webhook signature verification (HMAC of the body,
not just a shared header), Alembic migrations, and a proper eval set for the
live LLM path.

---

## HR and Behavioral (16)

**1. Tell me about yourself.**
Structure: present, project, proof, why here. "I'm a 2026 graduate who builds
end-to-end: my main project, Autom8r, is a working AI lead-qualification
platform with a FastAPI backend, a React frontend, and an MCP tool server,
covered by 67 automated tests. I built it to learn how LLM features actually
ship: prompts, tools, retrieval, failure modes. I want to apply that to real
communication products here."

**2. Why this company?**
Do your homework and connect it to the project. "You build communication
APIs: messaging, voice, webhooks. My project is literally a demo of what your
customers build on top of a CPaaS: a WhatsApp-support assistant that
qualifies leads and receives webhook events. I already think about your
domain: delivery retries, idempotency, signatures, and developer experience."

**3. Why should we hire you as a fresher?**
"I ship complete things, not tutorials: Autom8r has a frozen API contract,
typed errors, auth, idempotent webhooks, and 67 tests. I learn new
technology fast and from primary sources: I built on the current MCP Python
SDK (v2) by reading its docs, not a video. And I can explain my work clearly,
which I am doing right now."

**4. What are your strengths?**
Pick two, each with proof. "Ownership: I designed the whole Autom8r
architecture and documented every tradeoff in the code. Precision: my API
returns one error envelope with stable codes, and the contract doc and the
code never disagree, because I treat docs as part of the feature."

**5. What is your weakness?**
A real one, with the fix in progress. "I used to over-engineer early. On
Autom8r I caught myself designing a plugin system before the core flow
worked. Now I force the order: walking skeleton first, tests green, then
abstractions where the code proves they are needed."

**6. Tell me about a challenge you faced.**
Use the debugging framework. "Two processes sharing one SQLite file gave me
'database is locked' errors. I reproduced it with concurrent writes, isolated
the cause (default journal mode serializes readers and writers), diagnosed
the fix (WAL mode plus a busy timeout on every connection, in both
processes), applied it, and verified with a test that writes from both sides.
That fix is in `backend/app/db/database.py` and `mcp_server/db.py`."

**7. Tell me about a time you learned something new quickly.**
"MCP was new to me and the ecosystem had moved: older tutorials used the
deprecated SSE transport. I went to the official spec and the current Python
SDK, built the smallest possible server, tested it in-process with
`Client(server, mode="legacy")`, then wired it into the backend over
Streamable HTTP. Within the project I went from zero to a tested four-tool
server."

**8. How do you handle feedback on your code?**
"I want feedback early, on the smallest possible diff. When I get a comment
I first make sure I understand the 'why' behind it, then I fix it and add a
test or a doc line so the same issue cannot come back silently."

**9. Tell me about working in a team.**
If you have a college team story, use it; otherwise be honest: "Autom8r was
solo, so I simulated team discipline: a frozen API contract doc before
frontend work, conventional commits, and docs written for a reader who is
not me. In college group projects I was the one who integrated everyone's
parts and got the demo running."

**10. Tell me about a disagreement and how you handled it.**
"Disagreements I handle by moving from opinions to evidence: write both
options, compare them against the requirement, and pick by criteria, not by
who argued longer. In Autom8r I argued with myself over embeddings vs TF-IDF
that way, and the written tradeoff in `retrieval_service.py` is the result."

**11. How do you prioritize when everything is urgent?**
"Correctness first, then the user-visible path, then polish. A broken happy
path with great logging is still broken. In practice: make the core flow work
end to end, test it, then harden the edges."

**12. Where do you see yourself in two to three years?**
"Deep in backend and AI integration: the engineer the team trusts with the
LLM features that touch real customers. I want to grow from building a
working prototype to owning a production service, including its on-call
realities."

**13. Why software development?**
"Because it is the field where curiosity compounds. Every concept I learn
shows up in something I can build the same week. Autom8r started as 'how do
LLM agents actually call tools?' and ended as a full platform. That loop,
question to working software, is what I want to do every day."

**14. What do you do outside coursework?**
"I build. Autom8r is the big piece; I also read engineering docs and release
notes for the tools I use, because that is where the real changes are, like
the MCP transport change from SSE to Streamable HTTP."

**15. Are you comfortable with relocation or rotational shifts?**
Answer honestly and positively if true: "Yes. I am early in my career and my
priority is learning from a strong team; location and shift timing are
secondary to that."

**16. Do you have any questions for us?**
Always ask two. Good ones for a CPaaS: "How do your teams test webhook
delivery and retries for customers?" and "What does the first 90 days look
like for a fresher on this team?" and "Are you exploring LLM features on top
of your messaging APIs, and how?"
