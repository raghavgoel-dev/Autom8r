# MCP Explained (and How Autom8r Uses It)

This document explains the Model Context Protocol (MCP) from zero, in plain
language, and then shows exactly how this project puts it to work. Everything
in the second half is grounded in the code under `mcp_server/` and
`backend/app/services/mcp_client_service.py` (mcp SDK version 2.2.0).

---

## Part 1: What MCP is, and why it exists

### The problem it solves

An AI assistant that can only talk is limited. To be useful it needs to DO
things: look up a record, create a row in a CRM, fetch a document. Without a
standard, every assistant builder invents their own way to describe those
capabilities to the model, and every tool builder invents their own API
shape. N assistants times M tools means N x M custom integrations, each one
slightly different, each one breaking in its own way.

MCP (Model Context Protocol) is an open standard that sits between AI
applications and the systems they use. It defines one protocol for "here are
the things I can do, here is how to ask me to do them, and here is the
result." Build a tool server once, and any MCP-compatible assistant can use
it. Build an assistant once, and it can use any MCP tool server.

A useful mental model: MCP is to AI integrations what USB is to peripherals.
One socket shape, many devices, no custom wiring per pair.

### The three roles

- **Host:** the application the user interacts with that wants AI plus
  tools. In this project, the FastAPI backend is the host (more precisely,
  the `AgentService` inside it).
- **Client:** the protocol connection the host opens to a server. The host
  owns the client; one client per server connection. Here it is
  `MCPClientService`, a thin wrapper over the SDK's `Client` from
  `mcp.client`.
- **Server:** the process that exposes capabilities. Here it is the
  standalone `mcp_server` process, an `MCPServer` from
  `mcp.server.mcpserver` named `autom8r-lead-tools`.

The key point that surprises newcomers: the server is a SEPARATE PROCESS
with its own lifecycle. It does not live inside the web app. That is what
lets an IDE, Claude Desktop, or this backend all connect to the same server
without involving each other.

### Tools vs resources vs prompts

MCP servers expose three kinds of capabilities. This project has one of
each, so the distinction is easy to see:

- **Tools** are functions the model (or a policy) can ask the server to
  execute. They take arguments and return structured results. Think verbs:
  `create_lead`, `search_lead`, `update_lead`, `get_business_info`. Tools
  can have side effects, so each one carries `ToolAnnotations` describing
  its safety profile (more on that below).
- **Resources** are readable data, identified by a URI. Think nouns. This
  project serves the company information document at
  `business://company-info`. A client reads it like it would fetch a file;
  no arguments, no side effects.
- **Prompts** are reusable prompt templates a client can fetch. This project
  exposes `lead_qualification_prompt`, the same qualification guidance the
  backend keeps in `backend/app/prompts/qualification_prompt.txt`, so an
  external MCP host could pull the playbook straight from the server instead
  of the prompt living only in one app's codebase.

Rule of thumb: tools act, resources inform, prompts guide.

### MCP vs REST

They solve different problems and this repo deliberately contains both, so
you can compare them side by side:

|                        | REST (`/api/v1/leads`)              | MCP (`:8001/mcp`)                          |
|------------------------|-------------------------------------|--------------------------------------------|
| Audience               | Programmers writing clients         | AI models and agents at runtime            |
| Discovery              | Read docs / OpenAPI out of band     | `list_tools` returns schemas live          |
| Contract               | Endpoints, verbs, status codes      | Tool names, JSON Schema inputs, annotations|
| Who decides what to call | The calling code, hard-coded      | The model, using descriptions + schemas    |
| Session                | Stateless requests                  | A session with a handshake, then calls     |

REST says "here are fixed URLs; your code decides which to call." MCP says
"here is a self-describing menu of capabilities; the model decides which to
use, and the description text plus the input schema are how it decides."
That is why the tool descriptions in `mcp_server/tools/lead_tools.py` are
written so carefully ("Do NOT use for leads that already exist, use
update_lead for those"): the description is not documentation for humans, it
is runtime guidance for the model.

### Why a company would use MCP for AI integrations

1. **Write once, connect many.** The lead tools in this repo work for the
   FastAPI backend today and for any other MCP host tomorrow, unchanged.
2. **A hard boundary around side effects.** The AI never touches the
   database directly. It asks the server, the server validates and executes,
   and the audit trail lives at the boundary. In this project the agent
   literally has no database handle for chat-driven actions.
3. **Swappable assistants.** Because the backend talks to tools through the
   `MCPClientLike` protocol, the LLM can be mocked, swapped for another
   provider, or upgraded without touching the tools.
4. **Discovery beats documentation.** `GET /api/v1/admin/tools` does not
   read a spec file; it asks the live server what it can do right now.

---

## Part 2: How THIS project uses MCP

### The server

`mcp_server/server.py` builds the server with the current SDK (v2):

```python
from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="autom8r-lead-tools",
    version="0.1.0",
    instructions="Lead-management and business-information tools ...",
)
```

`create_server()` registers the tools, the resource, and the prompt, then
`main()` runs it over Streamable HTTP, the current standard transport:

```python
create_server().run(
    transport="streamable-http",
    host="127.0.0.1",          # MCP_HOST env override
    port=8001,                 # MCP_PORT env override
    streamable_http_path="/mcp",
)
```

One HTTP endpoint, `http://127.0.0.1:8001/mcp`, carries the whole protocol
session. It runs as its own process (`python -m mcp_server.server` from the
repo root) for the reasons covered in `docs/architecture.md`: real MCP
topology, and a proof that two processes can share one SQLite file safely.

### The tools

Four tools, registered with the `@mcp.tool` decorator in
`mcp_server/tools/`:

| Tool               | Mutates? | Annotations (verified in code)                                  |
|--------------------|----------|-----------------------------------------------------------------|
| `create_lead`      | yes      | `read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False` |
| `search_lead`      | no       | `read_only_hint=True,  destructive_hint=False, idempotent_hint=True,  open_world_hint=False` |
| `update_lead`      | yes      | `read_only_hint=False, destructive_hint=False, idempotent_hint=True,  open_world_hint=False` |
| `get_business_info`| no       | `read_only_hint=True,  destructive_hint=False, idempotent_hint=True,  open_world_hint=False` |

`ToolAnnotations` are machine-readable hints about a tool's behavior. A host
can use them to, for example, call read-only tools freely but confirm with a
human before destructive ones. This project sets them accurately and the
test suite pins them
(`test_tool_listing_has_four_tools_with_annotations`).

Each tool is a plain Python function with typed parameters. The SDK derives
the JSON Schema input contract from the signature, and the return type is a
frozen Pydantic model (`LeadResult`, `SearchResult`, `BusinessInfo`), which
is what lets results come back as structured content instead of
unstructured text.

```python
@mcp.tool(name="create_lead", title="Create Lead",
          description="Create a NEW sales lead in the CRM database ...",
          annotations=ToolAnnotations(read_only_hint=False, ...))
def create_lead(name: str, phone: str, email: str | None = None, ...) -> LeadResult:
    ...
```

Under the hood, lead tools use `LeadStore` (`mcp_server/db.py`), a small raw
`sqlite3` data layer with parameterized queries, and score every lead with
the shared `backend/app/services/scoring.py` module so REST-created and
MCP-created leads score identically.

### The resource

`business://company-info` serves the Markdown in
`mcp_server/resources/business_info.md`:

```python
@mcp.resource("business://company-info")
def business_company_info() -> str:
    return _read_business_info()
```

Note the URI scheme is `business://`, not `https://`. Resource URIs are just
identifiers; the scheme is a namespace you choose.

### The prompt

`lead_qualification_prompt` (`mcp_server/prompts/qualification_prompt.py`)
returns the qualification playbook: which fields to collect, in what order,
when to call `create_lead`, and the rule to never mention scores to the
customer. It mirrors `backend/app/prompts/qualification_prompt.txt` so an
external host and this backend speak from the same script.

### The client (backend side)

`backend/app/services/mcp_client_service.py` is the backend's only path to
the tools. Two design choices matter:

1. **Per-call connections.** Every operation is
   `async with Client(self._base_url) as client:` around exactly one
   `list_tools()` or `call_tool(name, arguments)`. No persistent session.
   A restarted MCP server can never leave a stale session behind, and the
   demo's call rate (at most one tool call per chat turn) makes the few
   milliseconds of handshake irrelevant. The `MCPClientLike` protocol means
   a pooled-session variant would only change this one class.
2. **Typed failures.** Any SDK or transport error becomes
   `MCPUnavailableError` (HTTP 503, `MCP_UNAVAILABLE`). A tool that ran but
   reported failure (`result.is_error`) becomes `MCPToolError` (HTTP 502,
   `MCP_TOOL_ERROR`). The agent catches both and degrades gracefully: the
   chat still answers, with an error entry in `tool_activity`, instead of
   crashing the turn.

Structured results come back via `result.structured_content` (a dict, since
the tools return Pydantic models). Tools without a structured schema would
fall back to the first text block.

### The shared-SQLite WAL story

Both processes write to `data/autom8r.db`. Two rules make that safe:

1. **WAL mode everywhere.** Both sides run `PRAGMA journal_mode=WAL` and
   `PRAGMA busy_timeout=15000` on every connection. Write-Ahead Logging lets
   readers and a writer coexist instead of taking a whole-file lock, which
   is what prevents "database is locked" errors between the backend and the
   MCP server.
2. **One datetime format.** SQLAlchemy's SQLite DATETIME type stores
   `'YYYY-MM-DD HH:MM:SS.ffffff'` (space-separated, UTC). The MCP server's
   `_now()` writes the exact same format, so a row created by either side
   reads correctly on the other. This is a documented contract in
   `mcp_server/db.py`.

### See it yourself

With the MCP server running, the backend proves connectivity live:

```
curl http://localhost:8000/api/v1/admin/tools -H "Authorization: Bearer change-me"
```

Stop the MCP server and the same call returns the 503 `MCP_UNAVAILABLE`
envelope. For an interactive look, the MCP Inspector works too:

```
npx @modelcontextprotocol/inspector
```

Connect with transport "Streamable HTTP" to `http://127.0.0.1:8001/mcp` and
you can list tools, call `search_lead`, read `business://company-info`, and
fetch `lead_qualification_prompt` from a GUI. The server's own tests do the
same thing in-process with no network at all:
`Client(server, mode="legacy")` connects the SDK client directly to the
`MCPServer` instance (see `mcp_server/tests/test_server.py`).
