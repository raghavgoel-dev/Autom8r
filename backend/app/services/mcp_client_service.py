"""MCP client service — the backend's only path to business tools.

WHY a per-call connection?
  WHAT: each tool call opens a short-lived Streamable HTTP session to the
        MCP server, calls, and closes.
  WHY: stateless and crash-proof — a restarted MCP server never leaves a
       stale session behind, and the demo's call rate is one tool per chat
       turn at most.
  TRADEOFF: a few ms of handshake per call vs. a persistent session pool.
       For production you'd keep a pooled session; the docs explain how.

Every failure becomes a typed error (MCPUnavailableError / MCPToolError) so
the agent can degrade gracefully and routes return clean 503/502 envelopes.
"""
from dataclasses import dataclass

from mcp.client import Client

from app.logging_config import get_logger
from app.services.llm_service import JSONValue
from app.utils.errors import MCPToolError, MCPUnavailableError

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MCPToolInfo:
    """One tool as discovered from the MCP server."""

    name: str
    description: str
    read_only: bool
    input_schema: dict[str, JSONValue]


class MCPClientService:
    """Thin async wrapper over the official MCP SDK client."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def list_tools(self) -> list[MCPToolInfo]:
        """Discover the tools the server currently exposes."""
        try:
            async with Client(self._base_url) as client:
                result = await client.list_tools()
        except Exception as exc:  # noqa: BLE001 — MCP boundary: any SDK/transport failure means "server unavailable"
            raise MCPUnavailableError(f"cannot reach MCP server: {exc!r}") from exc
        tools: list[MCPToolInfo] = []
        for tool in result.tools:
            annotations = tool.annotations
            tools.append(
                MCPToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    read_only=bool(annotations and annotations.read_only_hint),
                    input_schema=dict(tool.input_schema),
                )
            )
        return tools

    async def call_tool(
        self, name: str, arguments: dict[str, JSONValue]
    ) -> dict[str, JSONValue]:
        """Call one MCP tool and return its structured result.

        Raises MCPUnavailableError when the server cannot be reached and
        MCPToolError when the server ran the tool but reported failure.
        """
        logger.info("mcp tool call: %s", name)
        try:
            async with Client(self._base_url) as client:
                result = await client.call_tool(name, dict(arguments))
        except Exception as exc:  # noqa: BLE001 — MCP boundary, same rationale as list_tools
            logger.warning("mcp tool %s unreachable: %r", name, exc)
            raise MCPUnavailableError(f"cannot reach MCP server: {exc!r}") from exc

        if result.is_error:
            detail = _first_text(result) or "tool reported an error"
            logger.warning("mcp tool %s failed: %s", name, detail)
            raise MCPToolError(f"{name}: {detail}")

        logger.info("mcp tool %s succeeded", name)
        if result.structured_content is not None:
            return dict(result.structured_content)
        # Tools without a structured schema fall back to text content.
        return {"result": _first_text(result) or ""}


def _first_text(result: object) -> str | None:
    """Extract the first text block from a CallToolResult, if present."""
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            return text
    return None
