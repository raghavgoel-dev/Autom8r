"""POST /api/v1/chat — the conversational endpoint.

Public by design (spec section 12): a website visitor must be able to chat
without an account. The heavy lifting lives in AgentService; this route is
just the HTTP boundary.
"""
from fastapi import APIRouter, Request

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """Run one agent turn and return reply + lead + tool activity."""
    agent = request.app.state.agent
    return await agent.handle_chat(payload)
