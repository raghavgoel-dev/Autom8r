# Autom8r

**Automate conversations. Qualify leads. Connect tools.**

Autom8r is a working demonstration platform for AI-powered lead qualification
and customer support automation. A visitor chats with a conversational agent,
the agent collects their requirement turn by turn, qualifies the lead with a
deterministic scoring formula, and records it through an MCP tool server that
shares the same SQLite database as the REST API. Everything runs locally:
no API key, no database server, no external SaaS required.

> Status: a working prototype and learning project, verified end to end
> (tests + live browser + HTTP checks). It is not a production service.

## What it demonstrates

- A full-stack AI assistant: **React 18 + TypeScript + Vite** chat UI -> **FastAPI** agent endpoint -> retrieval (RAG) + LLM decision -> **MCP** tool call -> SQLite.
- **MCP (Model Context Protocol)** with the current Python SDK v2: a dedicated tool server (`mcp_server/`) exposing 4 tools, 1 resource, and 1 prompt over **Streamable HTTP**, discovered and called by the agent at runtime.
- **Conversational lead capture**: the agent extracts name, phone, business type, monthly enquiries, etc. across turns, then creates the lead _through MCP_ and reports the tool activity back to the UI.
- **Deterministic lead scoring** (0-100, priority bands low/medium/high) shared by both processes.
- **RAG from scratch**: pure-Python TF-IDF retrieval over `data/knowledge/*.md`, no vector database.
- **Two LLM modes**: a deterministic mock policy (default, no key needed) and a live OpenAI-compatible adapter that falls back to the mock on any failure.
- **Robustness**: typed error envelope across all endpoints, MCP/SQLite failure degradation, webhook idempotency, auth on admin + webhook routes.
- **Plug-and-play adapters**: optional Google Sheets lead sync behind a flag.

## Architecture in one picture

```text
Browser (React/Vite, :5173)
        |  fetch  (REST, error envelope)
        v
FastAPI backend (:8000)  <-  webhooks (:8000/api/v1/webhooks/lead)
   |  AgentService
   |   |- RetrievalService (TF-IDF over data/knowledge/*.md)
   |   |- LLMService (mock policy | OpenAI-compatible, tool calling)
   |   '- MCPClientService  (per-call client, Streamable HTTP)
   |                              |
   |                              v
   |                  MCP server (:8001/mcp)  [mcp_server/]
   |                    |- create_lead / search_lead / update_lead
   |                    |- business://company-info resource
   |                    '- lead_qualification_prompt
   |                              |
   '------------------------------+
                                  v
                       SQLite  data/autom8r.db  (WAL mode, shared)
                                  |
                                  v (optional)
                       Google Sheets append
```

Two Python processes (backend + MCP server) share one SQLite file. WAL mode
plus a busy timeout make that safe on local disk; both sides agree on the
same datetime storage format (`YYYY-MM-DD HH:MM:SS.ffffff`).

## Repository layout

```text
backend/        FastAPI app: REST CRUD, chat agent, webhooks, admin API
mcp_server/     MCP tool server (Python SDK v2, Streamable HTTP)
frontend/       React 18 + TS + Vite chat UI
data/knowledge/ RAG source docs (faq, products, policies) + seed samples
docs/           contract, architecture, API reference, agent flow, MCP,
                RAG, debugging, and interview-prep documentation
Makefile        convenience targets (optional; PowerShell below)
Dockerfile      single image; run twice for backend + MCP (see below)
docker-compose.yml  two-service local stack with a shared SQLite volume
```

## Prerequisites

- Python 3.13 (verified on 3.13.9)
- Node.js 18+ and npm (verified on Node 24 / npm 11)
- Git (optional)

## Quick start (three terminals)

```powershell
# Terminal 1 - MCP tool server (from repo root)
python -m pip install -r mcp_server/requirements.txt
python -m mcp_server.server
# -> Streamable HTTP server on http://127.0.0.1:8001/mcp

# Terminal 2 - FastAPI backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.db.seed          # optional: 8 fictional demo leads
uvicorn app.main:app --reload --port 8000
# -> API on :8000, interactive docs on http://localhost:8000/docs

# Terminal 3 - frontend
cd frontend
npm install
npm run dev
# -> http://localhost:5173
```

Then open http://localhost:5173 and chat. Try the demo conversation in
`docs/demo-checklist.md`, or the hand-rolled webhook in `data/samples`:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/webhooks/lead `
  -Headers @{ "X-Webhook-Secret" = "change-me" } `
  -ContentType "application/json" `
  -Body (Get-Content data\samples\sample_webhook.json -Raw)
```

Admin endpoints (replace the token):

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/stats `
  -Headers @{ Authorization = "Bearer change-me" }
```

## Configuration

Every variable has a working default, so `backend/.env` can stay untouched
for a first run. All configuration is centralized in `backend/app/config.py`.

| Variable | Default | What it controls |
|----------|---------|------------------|
| `MCP_SERVER_URL` | `http://127.0.0.1:8001/mcp` | MCP tool server address |
| `LLM_ENABLED` + `LLM_API_KEY` | `false` / empty | Both needed for live mode; otherwise the deterministic mock serves |
| `LLM_BASE_URL` / `LLM_MODEL` | empty / `gpt-4o-mini` | Any OpenAI-compatible endpoint |
| `ADMIN_TOKEN` / `WEBHOOK_SECRET` | `change-me` | Demo auth secrets, change them |
| `DATABASE_URL` | `<repo>/data/autom8r.db` | SQLite location (empty string -> default) |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins |
| `GOOGLE_SHEETS_ENABLED` `GOOGLE_SERVICE_ACCOUNT_JSON` `GOOGLE_SHEET_ID` | all empty | Optional best-effort lead sync to Google Sheets |
| `BACKEND_HOST` / `BACKEND_PORT` | `127.0.0.1` / `8000` | Where uvicorn binds (the README run command sets these explicitly) |

## How the agent works

Each chat turn flows through five stages (full detail: `docs/ai-agent-flow.md`):

1. **Retrieve** - rank knowledge chunks by TF-IDF cosine similarity (threshold 0.15, top 3).
2. **Extract** - accumulate lead fields from all user turns (name, phone, business type, enquiries, ...) plus short-answer question context.
3. **Decide** - the LLM chooses the next action:
   - **Mock mode** (deterministic policy): answer business-info intents, handle update/search intents, answer grounded knowledge questions, ask the next missing qualification question, or create the lead when capture is complete.
   - **Live mode** (OpenAI-compatible tool calling): the model calls MCP tools through the same tool loop (max 3 rounds). Any exception falls back to the mock policy for that turn.
4. **Act** - call the MCP tool (`create_lead`, `search_lead`, `update_lead`) or reply.
5. **Report** - each turn returns the reply, the current lead, `tool_activity` entries, and `retrieval_used` for honest UI reporting.

The 4-turn demo conversation (in `docs/demo-checklist.md` and
`docs/ai-agent-flow.md`) ends with a lead scored via the real shared formula:

| Field | Score |
|-------|-------|
| phone | +20 |
| email | +10 |
| requirement | +15 |
| business type | +15 |
| city | +10 |
| timeline within 3 months | +15 |
| monthly enquiries >= 300 | +15 |

Total is clamped to 0-100; **<40 low**, **40-69 medium**, **>=70 high**. The
Rahul demo captures phone + requirement + business type + ~500 enquiries =
**65, medium**.

## Tests

```powershell
cd backend
pytest            # 58 tests: health, auth, CRUD, chat qualification flow,
                  # MCP degradation, retrieval, scoring, webhooks

cd ..\mcp_server
pytest            # 9 tests: tools, resource, prompt, schema drift pin
```

67 tests total, all against throwaway databases (no state shared with your
dev DB).

## Docker (optional)

```powershell
docker compose up --build
```

Runs the MCP server and the backend as two services sharing a SQLite volume
(`:8001` MCP, `:8000` backend). The frontend still runs with `npm run dev`
in `frontend/`. Alternatively `docker build -t autom8r .` and run the image
twice (default CMD = backend; override with `python -m mcp_server.server`).

## Documentation

- `docs/architecture.md` - request path and the WHY/WHAT/HOW/TRADEOFF behind every technology choice
- `docs/api-contract.md` + `docs/api-reference.md` - the frozen HTTP contract, endpoint by endpoint with examples and errors
- `docs/mcp-explanation.md` - MCP from zero, then exactly how this project uses it
- `docs/ai-agent-flow.md` - one chat turn end to end, mock and live modes
- `docs/rag-explanation.md` - retrieval and RAG concepts vs this implementation
- `docs/debugging-guide.md` - symptom-to-fix for every common failure (Windows commands included)
- `docs/interview-questions.md`, `docs/learning-notes.md`, `docs/interview-project-explanation.md`, `docs/resume-bullets.md`, `docs/soft-skills.md`, `docs/demo-checklist.md` - interview and demo prep
- `backend/README.md`, `mcp_server/README.md`, `frontend/README.md` - per-package runbooks

## Security notes

- Secrets come from environment variables / `.env` only; nothing is hard-coded
  in source, and logs never print credentials (see `backend/app/logging_config.py`).
- The admin and webhook routes are guarded by bearer-token and
  `X-Webhook-Secret` comparison respectively (`hmac.compare_digest`), and the
  webhook endpoint is idempotent per `event_id`.
- The auth values are demo defaults (`change-me`). Change them before pointing
  anything public at the service.

## License

MIT, with a note that all data in this repository (companies, people,
phone numbers) is fictional. See `LICENSE`.