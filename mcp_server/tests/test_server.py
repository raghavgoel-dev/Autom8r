"""MCP server tests: tools, resource, and prompt over the in-process client.

Uses the official SDK pattern for server tests — ``Client(server, mode=
"legacy")`` connects directly to the MCPServer instance, no network needed.
"""
import pytest
from mcp.client import Client

from mcp_server.db import COLUMNS, LeadStore
from mcp_server.server import create_server


@pytest.fixture()
def store(tmp_path) -> LeadStore:
    """A LeadStore backed by a throwaway database file."""
    return LeadStore(tmp_path / "mcp-test.db")


@pytest.fixture()
def server(store: LeadStore):
    """The real MCP server wired to the throwaway store."""
    return create_server(store)


def test_schema_columns_match_backend_orm() -> None:
    """Given the shared database
    When LeadStore writes rows
    Then its column list matches the backend ORM (drift guard)."""
    assert COLUMNS == (
        "id", "name", "phone", "email", "city", "business_type", "budget",
        "requirement", "timeline", "monthly_queries", "lead_score",
        "priority", "status", "source", "created_at", "updated_at",
    )


async def test_tool_listing_has_four_tools_with_annotations(server) -> None:
    """Given the server
    When tools are listed
    Then all four exist with correct read-only annotations."""
    async with Client(server, mode="legacy") as client:
        result = await client.list_tools()
    tools = {tool.name: tool for tool in result.tools}
    assert set(tools) == {"create_lead", "search_lead", "update_lead", "get_business_info"}
    assert tools["search_lead"].annotations.read_only_hint is True
    assert tools["get_business_info"].annotations.read_only_hint is True
    assert tools["create_lead"].annotations.read_only_hint is False
    assert tools["update_lead"].annotations.idempotent_hint is True


async def test_create_lead_returns_structured_scored_lead(server) -> None:
    """Given the server
    When create_lead is called with the Rahul fields
    Then the structured result has the deterministic score."""
    async with Client(server, mode="legacy") as client:
        result = await client.call_tool(
            "create_lead",
            {
                "name": "Rahul", "phone": "9876543210",
                "business_type": "real estate", "monthly_queries": 500,
                "requirement": "WhatsApp customer support automation",
            },
        )
    assert result.is_error is False
    lead = result.structured_content
    assert lead["name"] == "Rahul"
    assert lead["lead_score"] == 65
    assert lead["priority"] == "medium"
    assert lead["status"] == "new"


async def test_search_lead_finds_created_lead(server) -> None:
    """Given a created lead
    When search_lead is called by phone fragment
    Then the lead is found."""
    async with Client(server, mode="legacy") as client:
        await client.call_tool("create_lead", {"name": "Priya", "phone": "9812345678"})
        result = await client.call_tool("search_lead", {"query": "9812345"})
    assert result.is_error is False
    assert result.structured_content["count"] == 1
    assert result.structured_content["leads"][0]["name"] == "Priya"


async def test_update_lead_changes_fields_and_recomputes(server) -> None:
    """Given a created lead
    When update_lead adds a city
    Then the city is stored and the score increases by 10."""
    async with Client(server, mode="legacy") as client:
        created = await client.call_tool(
            "create_lead", {"name": "Neha", "phone": "9898989898", "requirement": "sms alerts"}
        )
        before = created.structured_content["lead_score"]
        updated = await client.call_tool(
            "update_lead", {"phone": "9898989898", "city": "Pune"}
        )
    assert updated.is_error is False
    assert updated.structured_content["city"] == "Pune"
    assert updated.structured_content["lead_score"] == before + 10


async def test_update_lead_unknown_phone_is_a_tool_error(server) -> None:
    """Given no lead with a phone
    When update_lead is called
    Then the tool reports an error (is_error=True)."""
    async with Client(server, mode="legacy") as client:
        result = await client.call_tool("update_lead", {"phone": "0000000000", "city": "Pune"})
    assert result.is_error is True


async def test_business_resource_is_readable(server) -> None:
    """Given the server
    When business://company-info is read
    Then the markdown contains the company name."""
    async with Client(server, mode="legacy") as client:
        result = await client.read_resource("business://company-info")
    text = result.contents[0].text
    assert "Autom8r Demo Communications" in text


async def test_prompt_is_available(server) -> None:
    """Given the server
    When lead_qualification_prompt is fetched
    Then it returns qualification guidance."""
    async with Client(server, mode="legacy") as client:
        result = await client.get_prompt("lead_qualification_prompt", {})
    text = result.messages[0].content.text
    assert "phone" in text and "create_lead" in text


async def test_get_business_info_tool(server) -> None:
    """Given the server
    When get_business_info is called
    Then structured company info is returned."""
    async with Client(server, mode="legacy") as client:
        result = await client.call_tool("get_business_info", {})
    assert result.is_error is False
    assert result.structured_content["company_name"] == "Autom8r Demo Communications"
