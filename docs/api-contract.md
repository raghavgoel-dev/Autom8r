# Autom8r — Frozen API Contract

This is the **single source of truth** for the HTTP contract between the
React frontend and the FastAPI backend. The frontend agent and docs agents
MUST build against these exact shapes. If implementation changes a shape,
this file changes in the same commit.

Base URL (dev): `http://localhost:8000`
All bodies are JSON (`Content-Type: application/json`).

---

## Error envelope (ALL errors, every endpoint)

```json
{
  "success": false,
  "error": { "code": "LEAD_NOT_FOUND", "message": "Lead not found" }
}
```

Codes: `UNAUTHORIZED` (401), `LEAD_NOT_FOUND` (404), `MCP_UNAVAILABLE` (503),
`MCP_TOOL_ERROR` (502), `SHEETS_SYNC_ERROR` (502), `VALIDATION_ERROR` (422),
`INTERNAL_ERROR` (500).

FastAPI/Pydantic 422s are also wrapped in this envelope by a global handler.

---

## Lead object (`LeadOut`)

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

`priority`: `low | medium | high`. `status`: `new | contacted | qualified | converted | lost`.

---

## GET /health → 200

```json
{ "status": "ok", "app": "autom8r", "llm_mode": "mock", "version": "0.1.0" }
```

---

## Leads CRUD

- `GET /api/v1/leads` → 200. Optional query params: `status`, `priority`,
  `city`, `phone`, `limit` (1-100, default 20), `offset` (default 0).
- `GET /api/v1/leads/{id}` → 200 or 404 `LEAD_NOT_FOUND`.
- `POST /api/v1/leads` → 201. Body: `name` (req), `phone` (req, 7-15 digits
  after normalization), plus optional `email city business_type budget
  requirement timeline monthly_queries source`. Score/priority computed
  server-side.
- `PATCH /api/v1/leads/{id}` → 200. All fields optional; may also patch
  `status`, `priority`. Recomputes score only when a scoring field changes.
- `DELETE /api/v1/leads/{id}` → 204 (empty body). 404 if missing.

Success envelopes:

```json
// single
{ "success": true, "lead": { ...LeadOut } }
// list
{ "success": true, "count": 2, "leads": [ { ...LeadOut } ] }
```

---

## POST /api/v1/chat → 200 (public, no auth)

Request:

```json
{
  "message": "Rahul, 9876543210.",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Response:

```json
{
  "success": true,
  "reply": "Thanks Rahul! I've recorded your requirement...",
  "lead": { ...LeadOut } ,
  "tool_activity": [
    { "tool": "knowledge_search", "source": "retrieval", "status": "success", "summary": "Found 2 relevant knowledge chunks" },
    { "tool": "create_lead", "source": "mcp", "status": "success", "summary": "Lead #12 created" }
  ],
  "retrieval_used": true,
  "llm_mode": "mock"
}
```

- `lead` is `null` when no lead was created/updated this turn.
- `tool_activity` may be empty. `source`: `mcp | retrieval | local`.
  `status`: `success | error`.
- `llm_mode`: `mock | live` — the UI shows a "Mock LLM" badge when `mock`.
- When MCP is down, the chat still answers; tool_activity contains an
  `error` item and the reply says the action service is unavailable.

---

## POST /api/v1/webhooks/lead → 201 (header `X-Webhook-Secret`)

Body: `{ "event": "lead.created", "source": "website-demo", "timestamp": "...",
"event_id": "evt-1", "data": { "name": "Aman", "phone": "9999999999", ... } }`

Response 201: `{ "success": true, "duplicate": false, "lead": { ...LeadOut },
"message": "Lead created from webhook" }`
Duplicate `event_id` → 200 with `"duplicate": true`.
Missing/wrong secret → 401 `UNAUTHORIZED`.

---

## Admin (header `Authorization: Bearer <ADMIN_TOKEN>`)

`GET /api/v1/admin/stats` → 200:

```json
{
  "success": true,
  "stats": {
    "total_leads": 8, "new_leads": 3, "qualified_leads": 2,
    "high_priority_leads": 2, "medium_priority_leads": 4, "low_priority_leads": 2
  }
}
```

`GET /api/v1/admin/recent-leads?limit=5` → 200, same list envelope.

`GET /api/v1/admin/tools` → 200:

```json
{
  "success": true,
  "mcp_available": true,
  "tools": [
    { "name": "create_lead", "description": "...", "read_only": false }
  ]
}
```

MCP down → 503 `MCP_UNAVAILABLE`.

Missing/wrong token on any admin route → 401 `UNAUTHORIZED`.
