"""Business-knowledge MCP surface: the get_business_info tool + resource."""
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict

RESOURCE_URI = "business://company-info"
_INFO_PATH = Path(__file__).resolve().parent.parent / "resources" / "business_info.md"


class BusinessInfo(BaseModel):
    """Structured summary of the fictional demo company."""

    model_config = ConfigDict(frozen=True)

    company_name: str
    tagline: str
    summary: str
    details_markdown: str


def _read_business_info() -> str:
    """Read the business info markdown resource from disk."""
    return _INFO_PATH.read_text(encoding="utf-8")


def register_knowledge_tools(mcp: MCPServer) -> None:
    """Attach get_business_info and the business:// resource to the server."""

    @mcp.tool(
        name="get_business_info",
        title="Get Business Info",
        description=(
            "Retrieve official information about the company (what it does, "
            "products, contact, support hours). Use when the customer asks "
            "about the company itself. Read-only."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False,
            idempotent_hint=True, open_world_hint=False,
        ),
    )
    def get_business_info() -> BusinessInfo:
        """Return the company's official information (fictional demo data)."""
        markdown = _read_business_info()
        return BusinessInfo(
            company_name="Autom8r Demo Communications",
            tagline="Automate conversations. Qualify leads. Connect tools.",
            summary=(
                "Autom8r Demo Communications helps businesses automate customer "
                "conversations on WhatsApp, SMS, and voice: answering routine "
                "enquiries, qualifying leads, and handing complex chats to humans."
            ),
            details_markdown=markdown,
        )

    @mcp.resource(RESOURCE_URI)
    def business_company_info() -> str:
        """Serve the company information markdown as an MCP resource."""
        return _read_business_info()
