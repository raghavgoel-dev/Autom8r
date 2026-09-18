"""Chat endpoint schemas — the contract between the React UI and the agent.

The frontend renders ``reply``, updates its lead panel from ``lead``, and
renders one row per entry in ``tool_activity`` — so these shapes are frozen
and shared with the frontend agent in docs/api-contract.md.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.lead import LeadOut


class ChatMessage(BaseModel):
    """One conversational turn (used for client-supplied history)."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """POST /api/v1/chat payload.

    ``history`` is the client-kept conversation so far (stateless server):
    the agent uses it to understand follow-ups like "About 500."
    """

    model_config = ConfigDict(frozen=True)

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)


class ToolActivityItem(BaseModel):
    """One observable side effect of a chat turn, for the UI activity panel."""

    model_config = ConfigDict(frozen=True)

    tool: str
    source: Literal["mcp", "retrieval", "local"]
    status: Literal["success", "error"]
    summary: str


class ChatResponse(BaseModel):
    """POST /api/v1/chat response envelope."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    reply: str
    lead: LeadOut | None = None
    tool_activity: list[ToolActivityItem] = Field(default_factory=list)
    retrieval_used: bool = False
    llm_mode: Literal["mock", "live"] = "mock"
