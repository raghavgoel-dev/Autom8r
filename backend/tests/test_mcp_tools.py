"""Backend MCP client tests: typed failure modes when the server is down.

The happy path (real MCP round trip) is covered by mcp_server/tests and by
the chat tests with a fake client; here we pin the degraded behavior the
spec requires (spec section 57: MCP unavailable -> clean error, no crash).
"""
import pytest

from app.services.mcp_client_service import MCPClientService
from app.utils.errors import MCPToolError, MCPUnavailableError
from tests.conftest import ADMIN_HEADERS

DEAD_URL = "http://127.0.0.1:9/mcp"  # port 9 (discard) is never an MCP server


async def test_call_tool_raises_unavailable_when_server_down() -> None:
    """Given no MCP server listening
    When call_tool is attempted
    Then MCPUnavailableError is raised (not a raw connection error)."""
    client = MCPClientService(DEAD_URL)
    with pytest.raises(MCPUnavailableError):
        await client.call_tool("create_lead", {"name": "A", "phone": "9000000001"})


async def test_list_tools_raises_unavailable_when_server_down() -> None:
    """Given no MCP server listening
    When list_tools is attempted
    Then MCPUnavailableError is raised."""
    client = MCPClientService(DEAD_URL)
    with pytest.raises(MCPUnavailableError):
        await client.list_tools()


def test_admin_tools_returns_503_envelope_when_mcp_down(client) -> None:
    """Given the MCP server is not running
    When GET /api/v1/admin/tools is called with a valid token
    Then 503 MCP_UNAVAILABLE is returned in the standard envelope."""
    response = client.get("/api/v1/admin/tools", headers=ADMIN_HEADERS)
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "MCP_UNAVAILABLE"


def test_error_types_carry_http_metadata() -> None:
    """Given our typed errors, they know their status codes and codes."""
    assert MCPUnavailableError("x").status_code == 503
    assert MCPUnavailableError("x").code == "MCP_UNAVAILABLE"
    assert MCPToolError("x").status_code == 502
