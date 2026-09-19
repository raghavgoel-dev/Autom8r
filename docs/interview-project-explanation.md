# Explaining Autom8r in an Interview

Spoken-style scripts. Say them out loud until they sound like you, not like
the page. First person, plain words, numbers you can defend. Every claim here
is implemented and tested in the repo.

---

## The 30-second version

"Autom8r is a working prototype of an AI lead-qualification and support
assistant for a communications company. A website visitor chats with an AI
assistant; the assistant answers product questions from a small knowledge
base, collects the visitor's details naturally, and records a scored lead in
a CRM-style database. The interesting part is the architecture: the AI never
touches the database directly. It calls tools on a separate MCP server, the
Model Context Protocol, over HTTP. There's a React frontend, a FastAPI
backend, the MCP tool server, and a shared SQLite database, with 67 automated
tests. It also receives secured, idempotent webhooks, because that's how lead
events arrive in the real world."

## The 60-second version

"Autom8r is a demonstration platform for AI-powered lead qualification, the
kind of thing a CPaaS customer's success team would build. Three processes: a
React and TypeScript chat UI, a FastAPI backend, and a standalone MCP server
that exposes the business tools.

When a visitor asks 'What is your refund policy?', the backend retrieves the
answer from a local knowledge base using TF-IDF retrieval and grounds the
reply in it. When the conversation turns into a sales lead, the assistant
collects name, phone, business type, and monthly enquiry volume across a few
turns, then calls the create_lead tool on the MCP server. The server computes
a deterministic score, so sales sees a priority, not just a record.

Two design choices I'd highlight. First, the LLM is behind an interface: it
runs with a live OpenAI-compatible model, but falls back automatically to a
deterministic mock policy if the provider fails, so the demo and the tests
never depend on an API key. Second, everything the agent does to data goes
through MCP tools, the same protocol Claude Desktop and IDEs speak, so the
backend reads like a production agent system. The whole thing is covered by
67 tests, including a full chat-to-created-lead flow through the real MCP
server."

## The 2-minute version

Start with the 60-second version, then add:

"Let me walk you through one chat turn, because that's where the design
shows. A message arrives at POST /api/v1/chat. First, the backend runs
retrieval: the knowledge files are Markdown, split into chunks at each
section heading, scored with TF-IDF cosine similarity, and anything below a
threshold is treated as 'no knowledge'. Second, it re-derives the lead state
from the whole conversation history, which the client sends every turn, so
the server stays stateless. Third, the policy decides what to do: in live
mode that's an OpenAI-compatible tool-calling loop capped at three rounds; in
mock mode it's a deterministic rule policy that runs the same pipeline. If a
tool call is needed, it goes over Streamable HTTP to the MCP server, which
exposes four tools: create_lead, search_lead, update_lead, and
get_business_info, plus a business-info resource and a qualification prompt.

The scoring is transparent by design: phone is worth 20, email 10, a clear
requirement 15, business type 15, city 10, a timeline within three months 15,
and volume of 300 or more enquiries a month 15, clamped to 100. Low, medium,
and high bands at 40 and 70.

On reliability: every error returns one envelope with a stable code; the
webhook endpoint is protected by a shared secret compared in constant time
and dedupes redelivered events with an event ledger; and if the MCP server is
down, the API returns a 503 envelope and the chat degrades gracefully instead
of dying."

## The 5-minute version

Use the 2-minute version, then go deeper on demand. Anchor points to offer:

1. **Why MCP, really.** "I could have called the database from the agent
   directly. I didn't, for three reasons. The protocol boundary means the
   model can only do what four registered tools allow. The tools are
   self-describing, so any MCP host, my backend, an IDE, Claude Desktop, can
   discover and use them unchanged. And it forced me to handle the real
   failure modes: server unreachable versus tool-reported error, which map to
   503 and 502 in my API."

2. **The mock that isn't a mock.** "The deterministic mode isn't canned
   responses. It runs the same extraction, the same retrieval, and really
   calls the MCP tools; only the decision-maker is a rule policy instead of a
   model. That's why my tests can assert the full behavior offline, and why
   the live-to-mock fallback is safe: the mock exercises the same side
   effects."

3. **Two processes, one database.** "The backend uses SQLAlchemy; the MCP
   server uses raw parameterized SQL, deliberately, to show both idioms. They
   share one SQLite file in WAL mode with a busy timeout, which is what makes
   two-process sharing safe. A test pins the shared column list so schema
   drift fails loudly."

4. **Testing story.** "67 tests: 58 backend, 9 MCP. The MCP tests connect
   in-process with the SDK's client, no network. The chat tests replay a
   full four-turn conversation and assert the created lead has score 65,
   medium priority."

5. **What I'd do next.** "Embeddings behind the same retrieval interface,
   pooled MCP sessions, streaming responses, HMAC body signatures on the
   webhook, and Postgres when it outgrows one machine."

---

## Scripted answers to the questions you will get

### Why build Autom8r?

"I wanted to learn how LLM features actually ship, not how demos look. A
lead-qualification assistant forces all the real problems: grounding answers
in company documents, turning conversation into structured data, calling
tools safely, handling provider failures, and receiving events from outside
systems. I also picked the domain on purpose: communications automation is
the space I want to work in, and this project is a small, honest version of
what customers build on a CPaaS."

### Why FastAPI?

"Three reasons. Pydantic validation at the boundary: bad payloads become a
clean 422 before my code runs. Async-first: a chat turn is pure I/O waiting,
so an event loop serves it well. And automatic OpenAPI docs, which made the
frozen API contract easy to enforce. It's also the framework most Python
backend roles ask for right now."

### Why React?

"The UI is a chat with live side panels, lead data and tool activity, which
is component-shaped: each panel re-renders from the same response object.
React is also the most requested frontend skill, and pairing it with
TypeScript let me mirror the API contract as types, so a contract mismatch
fails at build time."

### Why SQLite?

"Zero-install: clone, seed, run, on any machine, including a fresh Windows
laptop. But the honest answer is that SQLite gave me a real engineering
problem to solve: the backend and the MCP server are two processes sharing
one file. WAL mode plus a busy timeout on every connection makes that safe.
And because the backend goes through SQLAlchemy, moving to PostgreSQL later
is a config change, not a rewrite. I know exactly where SQLite's ceiling is:
many concurrent writers or multiple machines."

### Why MCP?

"Because it's becoming the standard way agents call tools, and because it
enforces good architecture. The model can't run arbitrary code; it can only
invoke four registered, self-describing tools. The same server works for my
backend, an IDE, or Claude Desktop with zero changes. And it made failure
handling real: I distinguish 'server unreachable' from 'tool ran and
failed', and my API maps those to 503 and 502. I built it on the current
Python SDK, version 2: MCPServer on the server side, Client on the backend
side, Streamable HTTP as the transport."

### Why not just call APIs directly?

"Direct calls would work, and for a toy it would be less code. But then the
agent's capabilities are hardcoded in the backend, the tool schemas live in
two places, and nothing else can reuse them. With MCP, the server publishes
its tools with descriptions and JSON Schemas; the backend discovers them.
Adding a CRM tool later means registering one more tool on the server, with
no changes to the agent's plumbing. That's the difference between a script
and a platform."

### Why system prompts?

"Because behavior should be editable text, not code. My system prompt is a
file with eleven rules: be concise, treat retrieved knowledge as the source
of truth, use tools for actions, never claim a failed action succeeded, never
reveal internals, escalate to a human when asked. A separate qualification
prompt describes which lead fields to collect and in what order. Keeping them
as files means I can tune behavior without a deploy, and the same
qualification guidance is also exposed as an MCP prompt for other hosts."

### Why retrieval?

"The assistant answers questions about a specific company: its refund
policy, pricing, products. No base model knows that, and fine-tuning would be
overkill and stale the moment a document changes. Retrieval solves it: find
the relevant passage, put it in the prompt, answer from it. I used pure
Python TF-IDF over Markdown chunks, split at section headings, with a
similarity threshold. I chose it deliberately over embeddings: zero
dependencies, fully deterministic in tests, and honest about its weakness,
paraphrases. The swap to an embedding retriever is one class behind the same
interface, and that tradeoff is written in the code."

### How is the lead score calculated?

"It's a transparent heuristic, not an ML model, and I can defend every
point. Phone present: 20, because a lead you can call back is real. Email:
10. A clear requirement: 15. Business type: 15. City: 10. Timeline within
three months: 15, because urgency matters. Monthly enquiry volume of 300 or
more: 15, because that's where automation pays off. Sum, clamp to 0 to 100.
Bands: below 40 is low, 40 to 69 medium, 70 and above high. A worked example
from my tests: a visitor with a phone number, a WhatsApp-support requirement,
a real-estate business, and 500 monthly enquiries scores 20 + 15 + 15 + 15 =
65, medium. The same scoring module is imported by both the backend and the
MCP server, so a lead scores identically no matter which surface created it."

### How did you secure the webhooks?

"Two layers. Authentication: the sender includes a shared secret in the
X-Webhook-Secret header, and I compare it with hmac.compare_digest, a
constant-time comparison, so response timing can't leak the secret character
by character. Idempotency: every processed event_id is written to a ledger
table with a unique constraint; if the same event is delivered twice, which
happens all the time with real providers, I return 200 with duplicate: true
instead of creating a second lead. Wrong or missing secret is a 401 in the
standard error envelope. The production upgrade I can name: sign the whole
body with HMAC instead of a static header, and add replay timestamps."

### How did you handle errors?

"One rule: every error, from every endpoint, has the same shape:
success false, and an error object with a machine-readable code and a safe
message. Routes raise typed exceptions that carry their HTTP status and code;
global handlers convert them, including Pydantic's 422s and unexpected 500s,
into that envelope. Stack traces go to logs, never to clients. The codes are
frozen in the API contract: LEAD_NOT_FOUND, UNAUTHORIZED, VALIDATION_ERROR,
MCP_UNAVAILABLE, MCP_TOOL_ERROR, INTERNAL_ERROR. A client can program against
them, and my tests assert on them."

### What happens if the LLM fails?

"The turn still completes. The agent wraps the live path in a try: any
exception from the provider, timeout, rate limit, anything, is logged as a
warning, and the turn re-runs through the deterministic mock policy, which
does real work: same extraction, same retrieval, same MCP tool calls. The
response honestly reports llm_mode as mock, and the UI shows that badge. The
user gets a slightly simpler assistant for that turn, not an error page. In
tests I verified the fallback path, not just the happy path."

### What happens if MCP fails?

"Two distinct cases, two distinct answers. If the server is unreachable, the
client raises MCPUnavailableError: the admin tools endpoint returns a 503
envelope, and the chat still answers, because retrieval and conversation
don't need MCP, but it tells the user the lead-recording service is
temporarily unavailable and shows an error item in the activity panel. If
the server ran the tool and the tool reported failure, that's MCPToolError, a
502. The chat never dies either way; degradation is visible, not silent."

### How would you scale it?

"In order. First the database: managed PostgreSQL via the existing
DATABASE_URL setting, because a shared SQLite file is the first real ceiling.
The backend is stateless, history comes from the client, so it scales
horizontally behind a load balancer as-is. The MCP server scales the same
way, and I'd switch the client from per-call sessions to pooled sessions.
For the LLM path: cache retrieval results, use a smaller model for easy
turns, and keep the three-round tool cap. Retrieval would move to embeddings
in a vector store once the knowledge base outgrows in-memory TF-IDF. And I'd
add rate limiting on the public chat endpoint before any of that matters."

### How would you productionize it?

"Containers for all three processes, deployed to something like Cloud Run.
Postgres with Alembic migrations instead of create_all. Real authentication,
OAuth2 with JWTs, replacing the demo token, and HMAC-signed webhooks. Secrets
in a manager, not .env. Rate limiting and request size limits on the public
endpoints. Structured logs to a collector, metrics, and tracing; the
per-request and per-tool-call log lines are already there. CI running the 67
tests on every push. And an eval set for the live LLM path, so prompt changes
are measured, not vibes."

### What would you improve?

"Honest list, in priority order. Retrieval: embeddings behind the existing
interface, because paraphrase misses are TF-IDF's known cost. MCP client:
pooled sessions instead of per-call connections. Chat: streaming responses
for perceived latency. Webhooks: HMAC body signatures. Testing: a fixed eval
set for live mode. And the scoring heuristic could learn weights from real
conversion data once such data exists; I'd keep it explainable either way."
