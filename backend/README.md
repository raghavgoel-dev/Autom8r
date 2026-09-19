# Autom8r Backend

The FastAPI backend for Autom8r: REST lead CRUD, the conversational agent
endpoint, the webhook receiver, and the admin API. It is one of two Python
processes in the project; the other is the MCP tool server in
`../mcp_server/`, which this backend calls over Streamable HTTP.

This is a working demonstration platform, not a production service. It runs
with zero external dependencies beyond `pip install`: no API key needed
(deterministic mock LLM by default), no database server (SQLite in WAL
mode), no Google account (Sheets sync is optional and off by default).

All commands below are PowerShell-native and run from THIS directory
(`backend/`) unless noted. No `make` required.

## Setup

Requires Python 3.13 (developed and verified on 3.13.9).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

Copy the example env file and edit it:

```powershell
Copy-Item .env.example .env
```

Every variable has a working default, so an untouched copy is fine for a
first run. The ones you will actually care about:

| Variable | Default | What it controls |
|----------|---------|------------------|
| `MCP_SERVER_URL` | `http://127.0.0.1:8001/mcp` | Where the MCP tool server lives |
| `LLM_ENABLED` / `LLM_API_KEY` | `false` / empty | Both required for live LLM mode; otherwise the deterministic mock serves |
| `LLM_BASE_URL` / `LLM_MODEL` | empty | Any OpenAI-compatible endpoint; model defaults to `gpt-4o-mini` |
| `ADMIN_TOKEN` / `WEBHOOK_SECRET` | `change-me` | Demo auth secrets; change them |
| `DATABASE_URL` | repo-root `data/autom8r.db` | SQLite location (WAL mode is set per connection) |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins |
| `GOOGLE_SHEETS_ENABLED` (+2 more) | `false` | Optional best-effort lead sync to Google Sheets |

All configuration is centralized in `app/config.py`; nothing else reads the
environment directly.

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Then:

- API: `http://localhost:8000` (try `curl http://localhost:8000/health`)
- Interactive OpenAPI docs: `http://localhost:8000/docs`
- For the full system, also start the MCP server from the repo root in a
  second terminal: `python -m mcp_server.server`

## Seed demo data

```powershell
python -m app.db.seed
```

Inserts 8 fictional demo leads (scored with the real formula) if the table
is empty; safe to run repeatedly, it does nothing when leads exist.

## Tests

```powershell
pytest
```

58 tests covering health, auth, lead CRUD, the full chat qualification flow
(mock LLM with a fake MCP client), MCP failure degradation, retrieval,
scoring, and webhooks. Tests run against a throwaway temp database with
deterministic settings (see `tests/conftest.py`).

## Project structure

```
backend/
  app/
    main.py                  app assembly: middleware, error envelope, routers, lifespan
    config.py                every env var, typed (pydantic-settings)
    logging_config.py        one shared log format, never logs secrets
    api/routes/              HTTP boundary only, business logic lives in services
      health.py              GET /health (+ llm_mode)
      leads.py               GET/POST /api/v1/leads, GET/PATCH/DELETE /api/v1/leads/{id}
      chat.py                POST /api/v1/chat (public)
      webhooks.py            POST /api/v1/webhooks/lead (X-Webhook-Secret, idempotent)
      admin.py               GET /api/v1/admin/{stats,recent-leads,tools} (Bearer token)
    schemas/                 Pydantic v2 request/response models (the frozen contract)
    models/                  SQLAlchemy 2.0 ORM: Lead, WebhookEventRecord
    db/
      database.py            engine + WAL pragmas + create_all_tables
      session.py             per-request session dependency
      seed.py                fictional demo leads
    services/
      agent_service.py       chat turn orchestrator (retrieval -> decide -> tool -> reply)
      llm_service.py         LLMService protocol, MockLLMService, OpenAILLMService
      extraction.py          rule-based lead-field extraction (pure stdlib)
      retrieval_service.py   TF-IDF + cosine over data/knowledge/*.md (pure stdlib)
      scoring.py             deterministic lead scoring (shared with the MCP server)
      mcp_client_service.py  per-call MCP client, typed failures
      lead_service.py        CRUD, search, stats, scoring integration
      sheets_service.py      optional Google Sheets adapter (best-effort)
    prompts/                 system + qualification prompts (text files, not code)
    utils/                   typed errors, auth helpers, phone validation
  tests/                     pytest suite (58 tests)
  .env.example               copy to .env
  requirements.txt           pinned ranges; Google libs commented out (optional)
  pytest.ini
```

## Where to read next

- `../docs/architecture.md` - the full request path and the WHY behind each
  technology choice
- `../docs/api-reference.md` - every endpoint with examples and errors
- `../docs/ai-agent-flow.md` - one chat turn, end to end, with the verified
  four-turn demo conversation
- `../docs/debugging-guide.md` - symptom-to-fix for every common failure
