# Resume Bullets for Autom8r

Three variants of the same project entry. Every line describes a feature that
is implemented and covered by tests. No invented metrics, no "production",
no "customers". Use framing like: working prototype, demonstration platform,
modular architecture, local deployment, extensible design.

Project title for all variants: **Autom8r: AI lead-qualification and support
assistant (working prototype)**

---

## Variant A: Concise version

For a one-page resume where space is tight.

- Built a full-stack AI lead-qualification prototype: React + TypeScript chat
  UI, FastAPI backend, and a standalone MCP tool server, backed by 67
  automated tests.
- Implemented an agent that answers from a TF-IDF knowledge base, collects
  lead details over multi-turn chat, and records scored leads through MCP
  tools (4 tools, 1 resource, 1 prompt over Streamable HTTP).
- Designed for failure: deterministic mock LLM with a live OpenAI-compatible
  adapter and automatic fallback, typed error envelope across all endpoints,
  and a secured, idempotent webhook receiver.
- Solved two-process SQLite sharing with WAL mode and busy timeouts; backend
  on SQLAlchemy 2.0, MCP server on raw parameterized SQL.

## Variant B: ATS-friendly version

Keyword-dense, for applicant tracking systems. Keep the tech line verbatim.

**Tech: Python, FastAPI, React, TypeScript, SQL, LLM, RAG, MCP**

- Developed a demonstration platform for AI-powered lead qualification and
  customer support using Python, FastAPI, React, TypeScript, SQLAlchemy, and
  SQLite (WAL mode shared across two processes).
- Built an LLM agent with tool calling: retrieval-augmented generation (RAG)
  over a Markdown knowledge base using TF-IDF, multi-turn field extraction,
  and deterministic lead scoring (0 to 100, low/medium/high bands).
- Implemented a Model Context Protocol (MCP) server with the current Python
  SDK (MCPServer, Streamable HTTP transport) exposing 4 tools (create_lead,
  search_lead, update_lead, get_business_info), 1 resource, and 1 prompt;
  backend connects via an MCP client with typed 503/502 failure handling.
- Designed a dual-mode LLM architecture: deterministic mock policy for
  offline testing plus a live OpenAI-compatible adapter with automatic
  fallback and honest mode reporting.
- Implemented REST API with frozen contract: CRUD with correct status codes,
  Pydantic v2 validation, single error envelope with stable codes, Bearer
  token admin auth, and CORS configuration.
- Built a webhook receiver secured with a constant-time secret comparison
  (hmac.compare_digest) and an idempotency ledger that dedupes redelivered
  events.
- Wrote 67 automated tests (58 backend with FastAPI TestClient, 9 MCP server
  tests via in-process SDK client) covering CRUD, auth, webhook dedupe, chat
  flows, scoring, and retrieval.

## Variant C: Interview one-liner

For "walk me through your resume" and the top of a portfolio page.

"Autom8r is a working prototype of an AI lead-qualification assistant for a
communications company: a React chat UI, a FastAPI backend, and an MCP tool
server with 4 tools, a resource, and a prompt. The agent answers from a
TF-IDF knowledge base, qualifies leads across a conversation, and records
them with a transparent score; webhooks are secured and idempotent, the LLM
falls back to a deterministic mock when the provider fails, and 67 automated
tests keep the whole thing honest. Tech: Python, FastAPI, React, TypeScript,
SQL, LLM, RAG, MCP."

---

## Lines you must NOT use (and why)

- "Production-ready" / "enterprise-scale": it is a local prototype, and any
  interviewer can disprove the claim in one question. "Working prototype"
  plus real numbers is stronger.
- "Used by real customers" / "deployed to GCP": false. The deployment plan
  exists as an answer, not a fact.
- "Improved efficiency by X%": no such measurement exists. The honest numbers
  are 67 tests, 4 tools, 3 processes, 2 data-access idioms.
- "Expert in AI/ML": the project is AI integration with an explainable
  scoring heuristic, not ML model training. Say exactly that.

## Numbers you can always defend

- 67 automated tests (58 backend, 9 MCP server).
- 4 MCP tools, 1 resource, 1 prompt; Streamable HTTP transport; SDK mcp 2.x.
- Lead score: phone +20, email +10, requirement +15, business type +15,
  city +10, timeline within 3 months +15, volume of 300+ per month +15,
  clamped 0 to 100; bands at 40 and 70.
- 3 processes (frontend 5173, backend 8000, MCP server 8001); 1 shared
  SQLite file in WAL mode.
- A verified end-to-end conversation that creates a lead scoring 65
  (medium) through the real MCP server.
