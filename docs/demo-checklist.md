# Autom8r Demo Checklist (under 5 minutes)

A runbook for showing the project live, on Windows PowerShell. Practice it
twice before the interview. Every step lists the exact action, the expected
outcome, and where to look if it fails (details in
`docs/debugging-guide.md`).

The story this demo tells: a visitor asks a policy question (retrieval),
turns into a lead over four turns (agent + MCP tools), the lead is verified
in the database, updated and searched through chat, and a second lead arrives
through a secured webhook, all visible in admin stats.

---

## 0. One-time setup (before interview day)

From the repo root, in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r ..\mcp_server\requirements.txt
Copy-Item .env.example .env
cd ..\frontend
npm install
```

Defaults work untouched: `ADMIN_TOKEN=change-me`,
`WEBHOOK_SECRET=change-me`, mock LLM (no API key needed).

## 1. Start the three processes (three terminals)

**Terminal 1, MCP server (from the repo root):**

```powershell
python -m mcp_server.server
```

Expected: a server listening on `http://127.0.0.1:8001/mcp`.
If it fails: port 8001 busy or wrong directory; see
`docs/debugging-guide.md`, "Port already in use (Windows)".

**Terminal 2, backend (from `backend/`):**

```powershell
uvicorn app.main:app --reload --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`, plus a startup log line
showing `llm_mode=mock` and the MCP URL.
If it fails: port 8000 busy or venv not activated; see
`docs/debugging-guide.md`, "FastAPI won't start" and "Port already in use
(Windows)".

**Terminal 3, frontend (from `frontend/`):**

```powershell
npm run dev
```

Expected: Vite reports `Local: http://localhost:5173/`.
If it fails: dependencies not installed (`npm install`); see
`docs/debugging-guide.md`, "Frontend can't connect to the backend".

**Seed the demo leads (once, from `backend/`, any terminal):**

```powershell
python -m app.db.seed
```

Expected: `Seed complete: 8 demo leads inserted.` Running it again prints
that leads already exist and changes nothing (it is idempotent).
If it fails: database path or import error; see `docs/debugging-guide.md`,
"database is locked".

**30-second preflight (proves all three processes talk):**

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/api/v1/admin/tools -H "Authorization: Bearer change-me"
```

Expected: health returns `"status": "ok"` with `"llm_mode": "mock"`; the
tools call returns 200 with `"mcp_available": true` and four tools
(`create_lead`, `search_lead`, `update_lead`, `get_business_info`).
If the tools call returns 503 `MCP_UNAVAILABLE`: the MCP server (Terminal 1)
is not running or not on port 8001; see `docs/debugging-guide.md`, "MCP
connection failure (503 MCP_UNAVAILABLE)".

---

## 2. The 12-step demo sequence

### Step 1: Open the app

Action: open `http://localhost:5173` in the browser.
Expected: the chat UI loads: message thread, input box, lead panel, tool
activity panel, and a "Mock LLM" badge.
If it fails: blank page means the frontend or CORS; see
`docs/debugging-guide.md`, "Frontend can't connect to the backend" and
"CORS error in the browser console".

### Step 2: Ask a knowledge question

Action: send `What is your refund policy?`
Expected: the reply is grounded in the docs, starting with "Based on our
documentation (policies.md):" and quoting the 14-day money-back guarantee.
The activity panel shows a `knowledge_search` entry ("Found N relevant
knowledge chunk(s)"), and the retrieval indicator is on.
Narration: "No LLM magic here; that answer came from TF-IDF retrieval over
the Markdown knowledge base, chunk matched by cosine similarity."
If it fails: a generic reply instead of a grounded one means retrieval found
nothing; check that `data/knowledge/` exists and see
`docs/debugging-guide.md`, "When all else fails".

### Step 3: Rahul conversation, turn 1

Action: send `I am interested in automating WhatsApp customer support.`
Expected: the assistant asks about the business type ("What type of business
do you operate?").
Narration: "It extracted the requirement and is collecting the missing lead
fields in a natural order."
If it fails: see `docs/debugging-guide.md`, "MCP tool not found / tool
errors" and "When all else fails".

### Step 4: Rahul conversation, turn 2

Action: send `Real estate.`
Expected: the assistant asks for volume ("Approximately how many customer
enquiries do you receive per month?").
Narration: "A two-word answer only makes sense in context; the server
re-derives state from the history the client sends each turn."
If it fails: see `docs/debugging-guide.md`, "When all else fails".

### Step 5: Rahul conversation, turn 3

Action: send `About 500.`
Expected: the assistant asks for name and phone number.
Narration: "A bare number resolved by the last question asked; that is
question-context extraction, not a guess."
If it fails: see `docs/debugging-guide.md`, "When all else fails".

### Step 6: Rahul conversation, turn 4

Action: send `Rahul, 9876543210.`
Expected: the activity panel shows `create_lead` with status success ("Lead
#N created"), and the reply confirms: thanks Rahul, requirement recorded for
WhatsApp customer support automation, the team will call 9876543210.
Narration: "That tool call went over HTTP to a separate MCP server process;
the backend never touched the database for this."
If it fails: an apology about the lead-recording service means MCP is down;
see `docs/debugging-guide.md`, "MCP connection failure (503
MCP_UNAVAILABLE)".

### Step 7: Show the lead panel and tool activity

Action: point at the lead panel and the activity list.
Expected: the lead panel shows Rahul, phone 9876543210, business type real
estate, 500 monthly queries, requirement WhatsApp customer support
automation, lead score 65, priority medium, status new, source chat.
Narration: "Score 65 is explainable: phone 20, requirement 15, business type
15, volume over 300 worth 15. No email, city, or timeline, so it lands in
the medium band."
If the score differs: re-check the four turns were sent exactly as written,
then see `docs/debugging-guide.md`, "When all else fails".

### Step 8: Verify the database row

Action (any terminal, from the repo root):

```powershell
curl.exe "http://localhost:8000/api/v1/leads?phone=9876543210"
```

Optional, the raw file itself:

```powershell
python -c "import sqlite3; print(sqlite3.connect('data/autom8r.db').execute('SELECT id, name, phone, lead_score, priority, status, source FROM leads').fetchall())"
```

Expected: `count` 2, because the seed data already contains a "Rahul Sharma"
with the same phone number (phone is not unique in this schema). The list is
newest first, so the first lead is the one the chat just created: name Rahul,
`lead_score` 65, `priority` medium, `status` new, `source` chat. In the raw
query you also see all 8 seeded leads.
Narration: "Same row readable from both surfaces; the MCP server wrote it
with raw SQL, the backend reads it through SQLAlchemy, one shared WAL file.
And yes, there are two Rahuls with one phone now; the update tool always
picks the newest, which is the one we just made."
If it fails: empty list means the create did not happen; re-check step 6 and
see `docs/debugging-guide.md`, "database is locked".

### Step 9: Update the lead through chat

Action: send `update my city to Mumbai`
Expected: activity shows `update_lead` success ("Lead #N updated"); the reply
confirms the update; the lead panel now shows city Mumbai, score 75, priority
high.
Narration: "Adding the city recomputed the score: 65 plus 10 for city, and
75 crosses into the high band. Watch the priority flip."
If it fails: "cannot find your lead" means history was lost; restart the
conversation from step 3 and see `docs/debugging-guide.md`, "MCP tool not
found / tool errors".

### Step 10: Search through chat

Action: send `search Rahul`
Expected: activity shows `search_lead` success ("2 lead(s) found": your
chat-created Rahul plus the seeded Rahul Sharma); the reply reports the
newest match: Rahul (9876543210), status new, priority high.
Narration: "Search is a read-only MCP tool, annotated readOnlyHint, which is
how a host knows it is safe to call without confirmation."
If it fails: see `docs/debugging-guide.md`, "MCP connection failure (503
MCP_UNAVAILABLE)".

### Step 11: Fire the sample webhook

Action (any terminal, from the repo root):

```powershell
curl.exe -X POST http://localhost:8000/api/v1/webhooks/lead -H "Content-Type: application/json" -H "X-Webhook-Secret: change-me" -d "@data/samples/sample_webhook.json"
```

Expected: HTTP 201 with `"duplicate": false` and a new lead (Aman,
9999999999, source website-demo, score 45: phone 20 + requirement 15 + city
10, medium).
Then fire the exact same command again: HTTP 200 with `"duplicate": true`,
"Duplicate event ignored", and no second lead.
Narration: "The secret is compared in constant time, and the event ledger
makes redelivery safe. Retries are normal with real providers; duplicates
are not a bug here, they are handled."
Note: use `curl.exe`, not `curl`, in PowerShell; plain `curl` is an alias
for `Invoke-WebRequest` with different flags.
If it fails: 401 means the header or secret is wrong; 422 means the JSON
body did not parse; see `docs/debugging-guide.md`, "401 UNAUTHORIZED (admin
and webhook)" and "422 VALIDATION_ERROR".

### Step 12: Show admin stats

Action:

```powershell
curl.exe http://localhost:8000/api/v1/admin/stats -H "Authorization: Bearer change-me"
```

Expected: 200 with `total_leads` 10 (8 seeded + Rahul + Aman), `new_leads`
4 (2 seeded + Rahul + Aman), and the priority breakdown showing 7 high,
2 medium, 1 low after the city update pushed Rahul into the high band.
Bonus beat: run it without the header to show the 401 `UNAUTHORIZED`
envelope.
Narration: "One token, constant-time comparison, and every error in the same
envelope, that is the whole auth story, honestly scoped as demo auth."
If it fails: 401 means a wrong or missing token; see
`docs/debugging-guide.md`, "401 UNAUTHORIZED (admin and webhook)".

---

## 3. Reset for the next run

To reset the demo state, stop the backend and MCP server, delete the
database files, and re-seed:

```powershell
Remove-Item data\autom8r.db, data\autom8r.db-wal, data\autom8r.db-shm -ErrorAction SilentlyContinue
cd backend; python -m app.db.seed
```

## 4. If everything breaks on the day

Fall back to the tests; they are the demo without the demo gods:

```powershell
cd backend; pytest
cd ..\mcp_server; pytest
```

Expected: 58 passed (backend) and 9 passed (MCP server). Then say: "Every
flow I was going to show you is asserted in these tests, including the full
chat-to-created-lead conversation through the real MCP server."
