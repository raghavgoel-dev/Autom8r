"""Autom8r MCP server — business tools exposed over Model Context Protocol.

WHAT this is: a standalone process that exposes lead-management tools, a
business-info resource, and a qualification prompt via the current MCP
Python SDK (v2, ``MCPServer``), over Streamable HTTP at /mcp.

WHY a separate process (not mounted in FastAPI)?
  WHAT: runs on its own port (default 8001) with its own lifecycle.
  WHY: matches how MCP is used for real — any MCP host (this backend, an
       IDE, Claude Desktop) can connect to the same server without the
       FastAPI app being involved. It also proves the two-process story:
       backend (client) and MCP server share one SQLite file safely (WAL).
  TRADEOFF: one extra process to start locally vs. an in-process mount.

Run from the repository root:
    python -m mcp_server.server            # or: python mcp_server/server.py
"""
import os
import sys
from pathlib import Path

# Running as `python mcp_server/server.py` puts mcp_server/ on sys.path,
# hiding the backend package. Insert the repo root so the tools can import
# the shared scoring module either way.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.mcpserver import MCPServer

from mcp_server.db import LeadStore
from mcp_server.prompts.qualification_prompt import register_prompts
from mcp_server.tools.knowledge_tools import register_knowledge_tools
from mcp_server.tools.lead_tools import register_lead_tools


def create_server(store: LeadStore | None = None) -> MCPServer:
    """Build the MCP server with tools, resource, and prompt registered.

    Tests pass their own LeadStore (temp database); production uses the
    repo database from the environment.
    """
    server = MCPServer(
        name="autom8r-lead-tools",
        version="0.1.0",
        instructions=(
            "Lead-management and business-information tools for the Autom8r "
            "demo platform. create_lead/update_lead mutate; search_lead and "
            "get_business_info are read-only."
        ),
    )
    register_lead_tools(server, store or LeadStore.from_env())
    register_knowledge_tools(server)
    register_prompts(server)
    return server


def main() -> None:
    """Run the server over Streamable HTTP (the current standard transport)."""
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8001"))
    create_server().run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )


if __name__ == "__main__":
    main()
