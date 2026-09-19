# Autom8r API Reference

Base URL (development): `http://localhost:8000`

All request and response bodies are JSON (`Content-Type: application/json`).
The frozen contract this document is generated from lives in
`docs/api-contract.md`; the implementation lives in
`backend/app/api/routes/`. If a shape here ever disagrees with the running
server, the contract file and this document are updated in the same commit
as the code change.

Interactive OpenAPI docs are available at `http://localhost:8000/docs` while
the backend runs.

---

## Error envelope (every endpoint, every error)

No route builds error JSON by hand. Typed application errors
(`backend/app/utils/errors.py`) and two global handlers in
`backend/app/main.py` guarantee one shape:

```json
{
  "success": false,
  "error": { "code": "LEAD_NOT_FOUND", "message": "Lead not found" }
}
```

| Code               | HTTP | Raised when                                            |
|--------------------|------|--------------------------------------------------------|
| `UNAUTHORIZED`     | 401  | Missing or wrong admin Bearer token / webhook secret   |
| `LEAD_NOT_FOUND`   | 404  | The requested lead id does not exist                   |
| `VALIDATION_ERROR` | 422  | Pydantic rejected the payload (detail stays in logs)   |
| `MCP_TOOL_ERROR`   | 502  | The MCP server ran the tool but reported a failure     |
| `SHEETS_SYNC_ERROR`| 502  | Reserved for the Google Sheets adapter (see note)      |
| `MCP_UNAVAILABLE`  | 503  | The MCP server cannot be reached                       |
| `INTERNAL_ERROR`   | 500  | Anything unexpected (full traceback goes to the logs)  |

Note on `SHEETS_SYNC_ERROR`: the typed error exists in
`backend/app/utils/errors.py`, but the current Sheets adapter is
best-effort. A sync failure is logged and swallowed (the lead is already
safe in SQLite), so the API does not currently return this code. It is
defined for a future strict-sync variant.

---

## The Lead object (`LeadOut`)

Returned by lead-related endpoints, chat, and webhooks:

```json
{
  "id": 12,
  "name": "Rahul",
  "phone": "9876543210",
  "email": null,
  "city": null,
  "business_type": "real estate",
  "budget": null,
  "requirement": "WhatsApp customer support automation",
  "timeline": null,
  "monthly_queries": 500,
  "lead_score": 65,
  "priority": "medium",
  "status": "new",
  "source": "chat",
  "created_at": "2026-09-19T10:30:00Z",
  "updated_at": "2026-09-19T10:30:00Z"
}
```

Controlled vocabularies:

- `priority`: `low | medium | high`
- `status`: `new | contacted | qualified | converted | lost`

`lead_score` and `priority` are always computed server-side from the
deterministic formula in `backend/app/services/scoring.py`: phone +20,
email +10, requirement +15, business type +15, city +10, timeline within 3
months +15, monthly_queries >= 300 +15, clamped to 0-100. Bands: 0-39 low,
40-69 medium, 70-100 high.

---

## GET /health

Liveness probe. Also reports the active LLM mode so the UI can badge "Mock
LLM" honestly.

- **Auth:** none
- **Headers:** none

**Response 200**

```json
{ "status": "ok", "app": "autom8r", "version": "0.1.0", "llm_mode": "mock" }
```

`llm_mode` is `live` only when `LLM_ENABLED=true` and `LLM_API_KEY` is set;
otherwise `mock`.

**Errors:** none beyond `INTERNAL_ERROR` (500).

---

## GET /api/v1/leads

List leads, newest first, with optional exact-match filters.

- **Auth:** none
- **Query params:**

| Param      | Type | Default | Notes                          |
|------------|------|---------|--------------------------------|
| `status`   | str  | -       | exact match on status          |
| `priority` | str  | -       | exact match on priority        |
| `city`     | str  | -       | exact match                    |
| `phone`    | str  | -       | exact match (digits)           |
| `limit`    | int  | 20      | 1-100                          |
| `offset`   | int  | 0       | >= 0                           |

**Example**

```
GET /api/v1/leads?priority=high&limit=5
```

**Response 200**

```json
{
  "success": true,
  "count": 2,
  "leads": [ { "...LeadOut..." }, { "...LeadOut..." } ]
}
```

**Errors:** 422 `VALIDATION_ERROR` (e.g. `limit=0` or `limit=500`).

---

## POST /api/v1/leads

Create a lead. Score and priority are computed server-side; clients never
send them.

- **Auth:** none
- **Body:**

| Field             | Type | Required | Notes                                   |
|-------------------|------|----------|-----------------------------------------|
| `name`            | str  | yes      | 1-120 chars, not blank                  |
| `phone`           | str  | yes      | 7-15 digits after normalization         |
| `email`           | str  | no       | max 255                                 |
| `city`            | str  | no       | max 120                                 |
| `business_type`   | str  | no       | max 120                                 |
| `budget`          | str  | no       | max 120                                 |
| `requirement`     | str  | no       | free text                               |
| `timeline`        | str  | no       | max 120                                 |
| `monthly_queries` | int  | no       | >= 0                                    |
| `source`          | str  | no       | default `"api"`, max 50                 |

Phone normalization accepts common formatting: `+91 98765-43210` is stored
as `919876543210`.

**Example request**

```json
{
  "name": "Rahul",
  "phone": "9876543210",
  "business_type": "real estate",
  "requirement": "WhatsApp customer support automation",
  "monthly_queries": 500
}
```

**Response 201**

```json
{
  "success": true,
  "lead": {
    "id": 12, "name": "Rahul", "phone": "9876543210",
    "email": null, "city": null, "business_type": "real estate",
    "budget": null, "requirement": "WhatsApp customer support automation",
    "timeline": null, "monthly_queries": 500,
    "lead_score": 65, "priority": "medium", "status": "new",
    "source": "api",
    "created_at": "2026-09-19T10:30:00Z", "updated_at": "2026-09-19T10:30:00Z"
  }
}
```

**Errors:** 422 `VALIDATION_ERROR` (missing name, bad phone, blank name).

---

## GET /api/v1/leads/{id}

Fetch one lead by id.

- **Auth:** none

**Response 200**

```json
{ "success": true, "lead": { "...LeadOut..." } }
```

**Errors:** 404 `LEAD_NOT_FOUND` when the id does not exist.

---

## PATCH /api/v1/leads/{id}

Partially update a lead. Only fields present in the body change. The score
is recomputed only when a scoring field (`phone`, `email`, `requirement`,
`business_type`, `city`, `timeline`, `monthly_queries`) changes; an explicit
`priority` in the body is honored while `lead_score` is still recomputed.

- **Auth:** none
- **Body:** any subset of the `POST` fields plus `status` and `priority`
  (validated against the controlled vocabularies).

**Example request**

```json
{ "city": "Mumbai", "status": "contacted" }
```

**Response 200**

```json
{ "success": true, "lead": { "...LeadOut with city set..." } }
```

**Errors:** 404 `LEAD_NOT_FOUND`; 422 `VALIDATION_ERROR` (bad status value,
bad phone).

---

## DELETE /api/v1/leads/{id}

Delete a lead.

- **Auth:** none

**Response 204** with an empty body. (204 means "done, and there is nothing
to show you".)

**Errors:** 404 `LEAD_NOT_FOUND`.

---

## POST /api/v1/chat

Run one conversational turn with the AI agent. Public by design: a website
visitor must be able to chat without an account. The server is stateless;
the client keeps the conversation history and resends it each turn.

- **Auth:** none
- **Body:**

| Field     | Type  | Required | Notes                                      |
|-----------|-------|----------|--------------------------------------------|
| `message` | str   | yes      | 1-4000 chars                               |
| `history` | array | no       | up to 50 `{ "role", "content" }` turns, roles `user` / `assistant` |

**Example request**

```json
{
  "message": "Rahul, 9876543210.",
  "history": [
    { "role": "user", "content": "I am interested in automating WhatsApp customer support." },
    { "role": "assistant", "content": "Absolutely, I can help with that. What type of business do you operate?" },
    { "role": "user", "content": "Real estate." },
    { "role": "assistant", "content": "Thanks! Approximately how many customer enquiries do you receive per month?" },
    { "role": "user", "content": "About 500." },
    { "role": "assistant", "content": "Understood. Could you share your name and phone number so I can record your requirement?" }
  ]
}
```

**Response 200**

```json
{
  "success": true,
  "reply": "Thanks Rahul! I've recorded your requirement for WhatsApp customer support automation. Our team will reach out to you shortly at 9876543210.",
  "lead": { "...LeadOut, lead_score 65, priority medium..." },
  "tool_activity": [
    { "tool": "create_lead", "source": "mcp", "status": "success", "summary": "Lead #12 created" }
  ],
  "retrieval_used": false,
  "llm_mode": "mock"
}
```

Field notes:

- `lead` is `null` when no lead was created or updated this turn.
- `tool_activity` may be empty. `source` is `mcp | retrieval | local`;
  `status` is `success | error`. When retrieval grounded the reply, a
  `knowledge_search` item with source `retrieval` is prepended.
- `llm_mode` is `mock | live`, matching what actually served the turn (a
  live-mode failure that fell back to mock reports `mock`).
- When the MCP server is down, the endpoint still returns 200: the reply
  explains the lead-recording service is temporarily unavailable and
  `tool_activity` contains an `error` item. Chat degrades; it does not
  crash.

**Errors:** 422 `VALIDATION_ERROR` (empty message, bad role in history).

---

## POST /api/v1/webhooks/lead

Inbound event receiver. A webhook is the inverse of an API call: an external
system calls OUR endpoint when an event happens. Processing is idempotent
via an event ledger (`webhook_events` table): a redelivered `event_id` is
acknowledged as a duplicate instead of creating a second lead.

- **Auth:** header `X-Webhook-Secret: <WEBHOOK_SECRET>` (constant-time
  comparison)
- **Body:**

```json
{
  "event": "lead.created",
  "source": "website-demo",
  "timestamp": "2026-09-19T10:30:00Z",
  "event_id": "evt-demo-0001",
  "data": {
    "name": "Aman",
    "phone": "9999999999",
    "requirement": "customer support automation",
    "city": "Gurgaon"
  }
}
```

`event` must be the literal `"lead.created"`. `data` accepts `name`
(required), `phone` (required, normalized like the REST API), and optional
`email`, `city`, `business_type`, `requirement`, `monthly_queries`.
`timestamp` and `event_id` are optional; omitting `event_id` skips
deduplication. A ready-to-send sample lives at
`data/samples/sample_webhook.json`.

**Response 201 (new lead)**

```json
{
  "success": true,
  "duplicate": false,
  "lead": { "...LeadOut, source website-demo..." },
  "message": "Lead created from webhook"
}
```

**Response 200 (duplicate `event_id`)**

```json
{
  "success": true,
  "duplicate": true,
  "lead": null,
  "message": "Duplicate event ignored"
}
```

**Errors:** 401 `UNAUTHORIZED` (missing or wrong secret); 422
`VALIDATION_ERROR` (bad event name, bad phone).

---

## Admin endpoints

All three require the header `Authorization: Bearer <ADMIN_TOKEN>` and
return 401 `UNAUTHORIZED` when it is missing or wrong. This is deliberately
simple demo auth: one token, no roles, compared in constant time.

### GET /api/v1/admin/stats

Aggregate lead counts for the dashboard.

**Response 200**

```json
{
  "success": true,
  "stats": {
    "total_leads": 8,
    "new_leads": 3,
    "qualified_leads": 2,
    "high_priority_leads": 2,
    "medium_priority_leads": 4,
    "low_priority_leads": 2
  }
}
```

### GET /api/v1/admin/recent-leads

Newest leads for the admin panel.

- **Query params:** `limit` (int, 1-50, default 5)

**Response 200**

```json
{ "success": true, "count": 5, "leads": [ { "...LeadOut..." } ] }
```

**Errors:** 401, 422 (`limit` out of range).

### GET /api/v1/admin/tools

Live MCP tool discovery: proof that the backend can reach the MCP server.
Returns the tools the server currently exposes, with their descriptions and
read-only annotations.

**Response 200**

```json
{
  "success": true,
  "mcp_available": true,
  "tools": [
    { "name": "create_lead", "description": "Create a NEW sales lead ...", "read_only": false },
    { "name": "search_lead", "description": "Look up EXISTING leads ...", "read_only": true },
    { "name": "update_lead", "description": "Update fields on an EXISTING lead ...", "read_only": false },
    { "name": "get_business_info", "description": "Retrieve official information ...", "read_only": true }
  ]
}
```

**Errors:** 401; 503 `MCP_UNAVAILABLE` when the MCP server is down:

```json
{
  "success": false,
  "error": { "code": "MCP_UNAVAILABLE", "message": "cannot reach MCP server: ..." }
}
```

---

## Quick curl smoke test (PowerShell)

```powershell
# health
curl http://localhost:8000/health

# create a lead
curl -X POST http://localhost:8000/api/v1/leads `
  -H "Content-Type: application/json" `
  -d '{"name":"Rahul","phone":"9876543210","business_type":"real estate","monthly_queries":500}'

# chat
curl -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"message":"What is your refund policy?","history":[]}'

# admin (replace change-me with your ADMIN_TOKEN)
curl http://localhost:8000/api/v1/admin/stats -H "Authorization: Bearer change-me"

# webhook (replace change-me with your WEBHOOK_SECRET)
curl -X POST http://localhost:8000/api/v1/webhooks/lead `
  -H "Content-Type: application/json" -H "X-Webhook-Secret: change-me" `
  -d (Get-Content data\samples\sample_webhook.json -Raw)
```
