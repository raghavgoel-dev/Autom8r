"""Agent service — the conversational brain of Autom8r.

Flow for one chat turn (spec section 16):

    USER MESSAGE
      -> retrieve knowledge (TF-IDF)         [always]
      -> accumulate extracted lead fields    [always]
      -> decide: reply or tool call          [mock policy OR live model]
      -> execute tool via MCP client         [when decided]
      -> compose final reply

The agent never touches the database for chat-driven actions: create,
search, and update go through the MCP server, exactly like a production
setup where tools live behind a protocol boundary.
"""
import json
from typing import Literal

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)

from app.config import Settings
from app.logging_config import get_logger
from app.schemas.chat import ChatRequest, ChatResponse, ToolActivityItem
from app.schemas.lead import LeadOut
from app.services.llm_service import (
    ConversationContext,
    LLMService,
    MockLLMService,
    OpenAILLMService,
    accumulate_extraction,
    load_prompts,
)
from app.services.mcp_client_service import MCPClientLike
from app.services.retrieval_service import RetrievalService
from app.utils.errors import MCPToolError, MCPUnavailableError

logger = get_logger(__name__)

# A retrieval match below this cosine score is treated as "no knowledge".
RETRIEVAL_THRESHOLD = 0.15
# Hard cap on model<->tool round trips per chat turn (runaway protection).
MAX_TOOL_ROUNDS = 3


class AgentService:
    """Coordinates retrieval, the LLM policy, and MCP tool execution."""

    def __init__(
        self,
        settings: Settings,
        llm: LLMService | OpenAILLMService,
        mcp: MCPClientLike,
        retrieval: RetrievalService,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._mcp = mcp
        self._retrieval = retrieval

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Process one user message end to end."""
        message = request.message
        results = self._retrieval.retrieve(message, top_k=3)
        strong_match = bool(results and results[0].score >= RETRIEVAL_THRESHOLD)

        system_prompt, qualification_prompt = load_prompts()
        context = ConversationContext(
            message=message,
            history=tuple(request.history),
            # Live prompts get knowledge only on a strong match; the mock
            # policy decides for itself whether to consume it.
            knowledge=tuple(results) if (strong_match or self._llm.mode == "mock") else (),
            accumulated=accumulate_extraction(message, request.history),
            system_prompt=system_prompt,
            qualification_prompt=qualification_prompt,
        )

        activity: list[ToolActivityItem] = []
        served_mode: Literal["mock", "live"] = "live" if self._llm.mode == "live" else "mock"
        if isinstance(self._llm, OpenAILLMService):
            retrieval_used = strong_match
            try:
                reply, lead = await self._run_live(context, activity)
            except Exception as exc:  # noqa: BLE001 — spec section 57: any LLM failure degrades to mock
                logger.warning("live LLM failed (%r); falling back to mock", exc)
                served_mode = "mock"
                reply, lead, retrieval_used = await self._run_mock(context, activity)
        else:
            reply, lead, retrieval_used = await self._run_mock(context, activity)

        if retrieval_used:
            activity.insert(
                0,
                ToolActivityItem(
                    tool="knowledge_search",
                    source="retrieval",
                    status="success",
                    summary=f"Found {len(results)} relevant knowledge chunk(s)",
                ),
            )

        return ChatResponse(
            reply=reply,
            lead=lead,
            tool_activity=activity,
            retrieval_used=retrieval_used,
            llm_mode=served_mode,
        )

    # ------------------------------------------------------------------ mock

    async def _run_mock(
        self, context: ConversationContext, activity: list[ToolActivityItem]
    ) -> tuple[str, LeadOut | None, bool]:
        """Deterministic policy + at most one tool call per turn.

        Returns (reply, lead, used_knowledge) so the UI only reports
        retrieval when the answer was actually grounded in it.
        """
        mock = self._llm if isinstance(self._llm, MockLLMService) else MockLLMService()
        decision = mock.decide(context)
        if decision.reply is not None:
            return decision.reply, None, decision.used_knowledge

        tool = decision.tool_name or ""
        arguments = decision.tool_arguments or {}
        try:
            result = await self._mcp.call_tool(tool, arguments)
        except (MCPUnavailableError, MCPToolError) as exc:
            activity.append(
                ToolActivityItem(tool=tool, source="mcp", status="error", summary=exc.message)
            )
            return (
                "I have all your details, but our lead-recording service is "
                "temporarily unavailable. Please try again in a moment.",
                None,
                False,
            )

        activity.append(
            ToolActivityItem(
                tool=tool, source="mcp", status="success", summary=_summarize(tool, result)
            )
        )
        return _confirmation(tool, result), _lead_from_result(result), False

    # ------------------------------------------------------------------ live

    async def _run_live(
        self, context: ConversationContext, activity: list[ToolActivityItem]
    ) -> tuple[str, LeadOut | None]:
        """Model-driven tool loop (OpenAI-compatible function calling)."""
        llm = self._llm
        if not isinstance(llm, OpenAILLMService):
            raise MCPUnavailableError("live loop requires the live LLM service")

        messages = self._build_messages(context)
        tools = await self._openai_tools()
        lead: LeadOut | None = None

        for _round in range(MAX_TOOL_ROUNDS):
            completion = llm.create_completion(messages, tools)
            choice_message = completion.choices[0].message
            tool_calls = choice_message.tool_calls
            if not tool_calls:
                return choice_message.content or "...", lead

            messages.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=choice_message.content,
                    tool_calls=[
                        ChatCompletionMessageToolCallParam(
                            id=call.id,
                            type="function",
                            function={
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        )
                        for call in tool_calls
                    ],
                )
            )
            for call in tool_calls:
                name = call.function.name
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                try:
                    result = await self._mcp.call_tool(name, arguments)
                    activity.append(
                        ToolActivityItem(
                            tool=name, source="mcp", status="success",
                            summary=_summarize(name, result),
                        )
                    )
                    lead = _lead_from_result(result) or lead
                    payload = json.dumps(result)
                except (MCPUnavailableError, MCPToolError) as exc:
                    activity.append(
                        ToolActivityItem(tool=name, source="mcp", status="error", summary=exc.message)
                    )
                    payload = json.dumps({"success": False, "error": exc.message})
                messages.append(
                    ChatCompletionToolMessageParam(
                        role="tool", tool_call_id=call.id, content=payload
                    )
                )

        return (
            "I wasn't able to complete that action just now. "
            "Could you rephrase or try again?",
            lead,
        )

    def _build_messages(self, context: ConversationContext) -> list[ChatCompletionMessageParam]:
        """System + knowledge + history + current user message."""
        system = context.system_prompt + "\n\n" + context.qualification_prompt
        if context.knowledge:
            knowledge_text = "\n\n".join(
                f"[{item.document}]\n{item.chunk}" for item in context.knowledge
            )
            system += "\n\nRETRIEVED KNOWLEDGE (treat as the source of truth):\n" + knowledge_text
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system)
        ]
        for turn in context.history:
            if turn.role == "user":
                messages.append(ChatCompletionUserMessageParam(role="user", content=turn.content))
            else:
                messages.append(
                    ChatCompletionAssistantMessageParam(role="assistant", content=turn.content)
                )
        messages.append(ChatCompletionUserMessageParam(role="user", content=context.message))
        return messages

    async def _openai_tools(self) -> list[ChatCompletionToolParam]:
        """Discover MCP tools and convert to OpenAI function schemas."""
        try:
            discovered = await self._mcp.list_tools()
        except MCPUnavailableError:
            logger.warning("tool discovery failed (MCP down); model has no tools this turn")
            return []
        return [
            ChatCompletionToolParam(
                type="function",
                function={
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,  # MCP inputSchema IS JSON Schema
                },
            )
            for tool in discovered
        ]


def _lead_from_result(result: dict[str, object]) -> LeadOut | None:
    """Parse a tool result into a LeadOut when it looks like a lead record."""
    if "id" in result and "phone" in result:
        return LeadOut.model_validate(result)
    return None


def _summarize(tool: str, result: dict[str, object]) -> str:
    """One-line human summary of a tool result for the activity panel."""
    if tool == "create_lead" and "id" in result:
        return f"Lead #{result['id']} created"
    if tool == "update_lead" and "id" in result:
        return f"Lead #{result['id']} updated"
    if tool == "search_lead":
        return f"{result.get('count', 0)} lead(s) found"
    if tool == "get_business_info":
        return "Business info retrieved"
    return f"{tool} completed"


def _confirmation(tool: str, result: dict[str, object]) -> str:
    """User-facing confirmation after a successful mock-mode tool call."""
    if tool == "create_lead":
        name = result.get("name", "there")
        requirement = result.get("requirement")
        phone = result.get("phone", "")
        detail = f" for {requirement}" if requirement else ""
        return (
            f"Thanks {name}! I've recorded your requirement{detail}. "
            f"Our team will reach out to you shortly at {phone}."
        )
    if tool == "update_lead":
        return "Done — I've updated your details."
    if tool == "search_lead":
        count = result.get("count", 0)
        leads = result.get("leads")
        if count and isinstance(leads, list) and leads and isinstance(leads[0], dict):
            first = leads[0]
            return (
                f"Yes — I found {count} matching lead(s). Most recent: "
                f"{first.get('name')} ({first.get('phone')}), "
                f"status {first.get('status')}, priority {first.get('priority')}."
            )
        return "I couldn't find a lead matching that."
    if tool == "get_business_info":
        return str(result.get("summary", "Here is our company information."))
    return "Done."
