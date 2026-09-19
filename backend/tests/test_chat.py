"""Chat endpoint tests: mock LLM, tool flow, and degraded mode.

The agent's MCP dependency is replaced with a fake implementing the same
MCPClientLike protocol straight against the test database — so these tests
exercise the real agent logic and API contract without a network server.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.session import SessionLocal
from app.schemas.lead import LeadCreate, LeadOut, LeadUpdate
from app.services import lead_service
from app.services.agent_service import AgentService
from app.services.llm_service import MockLLMService
from app.services.mcp_client_service import MCPToolInfo
from app.services.retrieval_service import RetrievalService
from app.utils.errors import MCPToolError, MCPUnavailableError


class FakeMCP:
    """Test double for MCPClientService: same protocol, no network."""

    def __init__(self, failing: bool = False) -> None:
        self._failing = failing

    async def list_tools(self) -> list[MCPToolInfo]:
        """Mirror the real server's four tools."""
        return [
            MCPToolInfo(name=name, description="", read_only=read_only, input_schema={})
            for name, read_only in (
                ("create_lead", False), ("search_lead", True),
                ("update_lead", False), ("get_business_info", True),
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute the equivalent of each MCP tool on the test database."""
        if self._failing:
            raise MCPUnavailableError("fake MCP outage")
        if name == "create_lead":
            with SessionLocal() as db:
                lead = lead_service.create_lead(db, LeadCreate(**arguments))
                return LeadOut.model_validate(lead).model_dump(mode="json")
        if name == "search_lead":
            with SessionLocal() as db:
                leads = lead_service.search_leads(db, str(arguments.get("query", "")))
                return {
                    "count": len(leads),
                    "leads": [
                        LeadOut.model_validate(lead).model_dump(mode="json")
                        for lead in leads
                    ],
                }
        if name == "update_lead":
            phone = str(arguments.get("phone", ""))
            updates = {key: value for key, value in arguments.items() if key != "phone"}
            with SessionLocal() as db:
                exact = [lead for lead in lead_service.search_leads(db, phone) if lead.phone == phone]
                if not exact:
                    raise MCPToolError(f"no lead found with phone {phone}")
                lead = lead_service.update_lead(db, exact[0].id, LeadUpdate(**updates))
                return LeadOut.model_validate(lead).model_dump(mode="json")
        if name == "get_business_info":
            return {"summary": "Autom8r Demo Communications (fake)"}
        raise MCPToolError(f"unknown tool {name}")


@pytest.fixture()
def chat_client(client: TestClient) -> TestClient:
    """A client whose agent uses the fake MCP + mock LLM."""
    client.app.state.agent = AgentService(
        settings=settings,
        llm=MockLLMService(),
        mcp=FakeMCP(),
        retrieval=RetrievalService(),
    )
    return client


@pytest.fixture()
def degraded_client(client: TestClient) -> TestClient:
    """A client whose MCP is down (fake outage)."""
    client.app.state.agent = AgentService(
        settings=settings,
        llm=MockLLMService(),
        mcp=FakeMCP(failing=True),
        retrieval=RetrievalService(),
    )
    return client


def _chat(client: TestClient, text: str, history: list) -> dict:
    """Send one chat turn and append both sides to history."""
    response = client.post("/api/v1/chat", json={"message": text, "history": history})
    assert response.status_code == 200, response.text
    body = response.json()
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": body["reply"]})
    return body


def test_full_qualification_conversation_creates_lead(chat_client: TestClient) -> None:
    """Given the spec's four-turn conversation
    When the customer completes it
    Then a lead is created through the tool flow with score 65/medium."""
    history: list = []
    first = _chat(chat_client, "I am interested in automating WhatsApp customer support.", history)
    assert "business" in first["reply"].lower()
    second = _chat(chat_client, "Real estate.", history)
    assert "enquiries" in second["reply"].lower()
    third = _chat(chat_client, "About 500.", history)
    assert "name and phone" in third["reply"].lower()
    final = _chat(chat_client, "Rahul, 9876543210.", history)

    assert final["llm_mode"] == "mock"
    assert final["lead"] is not None
    lead = final["lead"]
    assert lead["name"] == "Rahul"
    assert lead["phone"] == "9876543210"
    assert lead["business_type"] == "real estate"
    assert lead["monthly_queries"] == 500
    assert lead["lead_score"] == 65
    assert lead["priority"] == "medium"
    assert lead["source"] == "chat"
    tools = [(item["tool"], item["status"]) for item in final["tool_activity"]]
    assert ("create_lead", "success") in tools
    assert "recorded" in final["reply"].lower()


def test_knowledge_question_uses_retrieval(chat_client: TestClient) -> None:
    """Given a policy question
    When chat is called
    Then the answer is grounded in the knowledge base."""
    body = _chat(chat_client, "What is your refund policy?", [])
    assert body["retrieval_used"] is True
    assert "14-day" in body["reply"]
    assert body["tool_activity"][0]["tool"] == "knowledge_search"


def test_greeting_turn_needs_no_tools(chat_client: TestClient) -> None:
    """Given a bare greeting
    When chat is called
    Then the assistant greets back without any tool activity."""
    body = _chat(chat_client, "Hi", [])
    assert "autom8r" in body["reply"].lower()
    assert body["tool_activity"] == []
    assert body["lead"] is None


def test_degraded_mode_when_mcp_down(degraded_client: TestClient) -> None:
    """Given the MCP server is unreachable
    When the customer completes their details
    Then the chat still answers 200 with a clear degraded message and an
    error entry in the activity panel (spec section 57)."""
    history: list = []
    _chat(degraded_client, "I want to automate WhatsApp support.", history)
    _chat(degraded_client, "Real estate.", history)
    _chat(degraded_client, "About 500.", history)
    final = _chat(degraded_client, "Rahul, 9876543210.", history)

    assert final["lead"] is None
    assert "temporarily unavailable" in final["reply"]
    errors = [item for item in final["tool_activity"] if item["status"] == "error"]
    assert errors and errors[0]["tool"] == "create_lead"


def test_search_flow_reports_match(chat_client: TestClient) -> None:
    """Given an existing lead
    When the customer asks to search
    Then search_lead runs and the reply names the match."""
    history: list = []
    _chat(chat_client, "I am interested in automating WhatsApp customer support.", history)
    _chat(chat_client, "Real estate.", history)
    _chat(chat_client, "About 500.", history)
    _chat(chat_client, "Rahul, 9876543210.", history)

    result = _chat(chat_client, "search Rahul", [])
    tools = [(item["tool"], item["status"]) for item in result["tool_activity"]]
    assert ("search_lead", "success") in tools
    assert "Rahul" in result["reply"]
