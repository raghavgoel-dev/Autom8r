# Autom8r MCP Server

A standalone Model Context Protocol server that exposes Autom8r's business
capabilities (lead management and company information) to any MCP host. The
FastAPI backend in `../backend/` is one such host; an IDE, Claude Desktop,
or the MCP Inspector could be another, with no code changes here.

Built on the official MCP Python SDK, version 2.2.0 (`MCPServer` from
`mcp.server.mcpserver`), served over Streamable HTTP at `/mcp`. It runs as
its own process on purpose: that is how MCP is used for real, and it proves
two processes can share one SQLite file safely (WAL mode, see
`../docs/mcp-explanation.md`).

All commands below are PowerShell-native. No `make` required.

## Setup

Requires Python 3.13 (developed and verified on 3.13.9). From THIS
directory (`mcp_server/`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

One shared venv at the repo root works too, as long as `mcp` and `pytest`
are installed. The tools import the backend's pure-stdlib scoring module
(`backend/app/services/scoring.py`), so both surfaces score leads
identically; `server.py` puts the repo root on `sys.path` to make that work
however the server is launched.

## Run

From the REPOSITORY ROOT (one level up):

```powershell
python -m mcp_server.server
```

(`python mcp_server/server.py` works as well.) Defaults: host `127.0.0.1`,
port `8001`, endpoint `http://127.0.0.1:8001/mcp`. Overrides:

```powershell
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8002"
$env:AUTOM8R_DB_PATH = "C:\path\to\other.db"   # default: <repo>/data/autom8r.db
python -m mcp_server.server
```

## What it exposes

### Tools (4)

| Tool | What it does | Annotations |
|------|--------------|-------------|
| `create_lead` | Create a NEW lead (name + phone required, more fields optional). Score and priority computed server-side. | mutating, not idempotent |
| `search_lead` | Find existing leads by phone or name fragment (up to 20, newest first). | read-only, idempotent |
| `update_lead` | Update fields on an existing lead, located by phone; recomputes the score. Errors when no lead has that phone. | mutating, idempotent |
| `get_business_info` | Official (fictional) company info: name, tagline, summary, full Markdown. | read-only, idempotent |

Descriptions are written for the model, not just for humans: they say when
to use each tool and when NOT to ("Do NOT use for leads that already
exist"). That text is how an LLM decides what to call.

### Resource (1)

`business://company-info` - the company information Markdown from
`resources/business_info.md`, readable by any client.

### Prompt (1)

`lead_qualification_prompt` - the qualification playbook (which fields to
collect, in what order, when to call `create_lead`, never mention scores to
the customer). Mirrors `../backend/app/prompts/qualification_prompt.txt`.

## Try it with MCP Inspector

With the server running:

```powershell
npx @modelcontextprotocol/inspector
```

In the Inspector UI, choose transport "Streamable HTTP" and enter
`http://127.0.0.1:8001/mcp`. You can then list the tools, call
`create_lead` / `search_lead` with JSON arguments, read
`business://company-info`, and fetch `lead_qualification_prompt`, all from
the GUI. (Requires Node.js for `npx`.)

You can also verify connectivity through the backend:

```powershell
curl http://localhost:8000/api/v1/admin/tools -H "Authorization: Bearer change-me"
```

## Tests

From THIS directory:

```powershell
pytest
```

9 tests. They run the real server in-process with the SDK's test client
(`Client(server, mode="legacy")`), so no network and no separate process is
needed. Coverage: the tool list and annotations, create/search/update with
the deterministic score (the Rahul fields produce exactly 65/medium), the
unknown-phone tool error, the resource, the prompt, and a drift guard
pinning the database column list to the backend ORM.

## Files

```
mcp_server/
  server.py            MCPServer assembly + Streamable HTTP entrypoint
  db.py                LeadStore: raw sqlite3, WAL pragmas, shared datetime format
  tools/
    lead_tools.py      create_lead / search_lead / update_lead (+ shared scoring)
    knowledge_tools.py get_business_info + the business://company-info resource
  prompts/
    qualification_prompt.py  lead_qualification_prompt
  resources/
    business_info.md   fictional company info (served as the resource)
  tests/test_server.py in-process SDK client tests (9)
  requirements.txt     mcp, pytest, pytest-asyncio
  pytest.ini
```

Two contracts keep this process compatible with the backend: the shared
scoring module, and the datetime storage format `'YYYY-MM-DD HH:MM:SS.ffffff'`
(space-separated, UTC) that SQLAlchemy's SQLite DATETIME type uses. Rows
written by either side read correctly on the other. See
`../docs/mcp-explanation.md` for the full story.
