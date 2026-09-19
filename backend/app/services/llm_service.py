"""LLM abstraction: one interface, two implementations.

WHY an abstraction?
  WHAT: ``LLMService`` protocol with ``OpenAILLMService`` (live) and
        ``MockLLMService`` (deterministic, offline).
  WHY: provider-specific code lives in exactly one class. The agent service
       talks to the protocol, so switching providers — or running with no
       API key at all — touches nothing else.
  TRADEOFF: one extra layer vs. sprinkling ``openai`` calls through the agent.

The mock is NOT a canned-response chatbot: it runs the same extraction,
retrieval, and tool-call flow as live mode, with a deterministic policy in
place of the model (spec section 36).
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeAlias

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.config import Settings
from app.logging_config import get_logger
from app.schemas.chat import ChatMessage
from app.services.extraction import (
    ExtractedLead,
    extract_bare_number,
    extract_business_type,
    extract_lead_fields,
    extract_monthly_queries,
    extract_name_phone_pair,
    extract_phone,
)
from app.services.retrieval_service import RetrievalResult

logger = get_logger(__name__)

# Recursive JSON type for tool arguments/results crossing the LLM boundary.
JSONValue: TypeAlias = (
    "str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]"
)
ToolArguments = dict[str, JSONValue]

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_QUESTION_STARTERS = (
    "what", "how", "do you", "does", "is ", "are ", "can you", "which",
    "tell me", "when", "where", "why", "who",
)

# Intent vocabularies for the mock policy (checked before lead collection).
_BUSINESS_INFO_INTENTS = (
    "who are you", "about your company", "about the company", "company info",
    "contact details", "where are you located",
)
_UPDATE_INTENTS = ("update", "change", "correct")
_SEARCH_INTENTS = (
    "search", "find lead", "find my", "look up", "check if", "do you have my",
    "is registered",
)
_SEARCH_STOPWORDS = re.compile(
    r"\b(search|find|look|up|check|if|lead|my|for|do|you|have|is|registered|"
    r"please|me|the|a|an)\b"
)


@dataclass(frozen=True, slots=True)
class LLMDecision:
    """What the agent should do next: reply to the user, or call a tool.

    Exactly one of ``reply`` / ``tool_name`` is set. ``used_knowledge`` marks
    replies grounded in retrieved knowledge (drives honest UI reporting).
    """

    reply: str | None = None
    tool_name: str | None = None
    tool_arguments: ToolArguments | None = None
    used_knowledge: bool = False


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Everything the LLM (or mock policy) sees for one turn."""

    message: str
    history: tuple[ChatMessage, ...]
    knowledge: tuple[RetrievalResult, ...]
    accumulated: ExtractedLead
    system_prompt: str = ""
    qualification_prompt: str = ""


def load_prompts() -> tuple[str, str]:
    """Read the system + qualification prompts from disk (kept out of code)."""
    system = (_PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")
    qualification = (_PROMPTS_DIR / "qualification_prompt.txt").read_text(encoding="utf-8")
    return system, qualification


class LLMService(Protocol):
    """The agent's view of any language model backend."""

    @property
    def mode(self) -> str:
        """'live' or 'mock' — surfaced to the UI as a badge."""
        ...

    def decide(self, context: ConversationContext) -> LLMDecision:
        """Choose the next action for one conversational turn."""
        ...


def _is_knowledge_question(message: str) -> bool:
    """Heuristic: interrogative phrasing or ends with a question mark."""
    lowered = message.strip().lower()
    return lowered.endswith("?") or lowered.startswith(_QUESTION_STARTERS)


def _short_phrase(message: str) -> str | None:
    """A cleaned short answer ('Real estate.' -> 'real estate'), else None."""
    cleaned = message.strip().strip(".!").strip()
    words = cleaned.split()
    if 1 <= len(words) <= 4 and not any(ch.isdigit() for ch in cleaned):
        return cleaned.lower()
    return None


class MockLLMService:
    """Deterministic stand-in for a real model.

    Policy (fully explainable, no randomness):
      1. Knowledge question + retrieval hit -> answer from the top chunk.
      2. Otherwise accumulate extracted lead fields, interpreting short
         answers using the last question the assistant asked.
      3. Enough fields -> call create_lead; otherwise ask the next question.
    """

    @property
    def mode(self) -> str:
        return "mock"

    def decide(self, context: ConversationContext) -> LLMDecision:
        message = context.message
        lead = context.accumulated
        lowered = message.lower()

        if any(intent in lowered for intent in _BUSINESS_INFO_INTENTS):
            return LLMDecision(tool_name="get_business_info", tool_arguments={})
        if any(intent in lowered for intent in _UPDATE_INTENTS):
            return self._update_decision(message, lead)
        if any(intent in lowered for intent in _SEARCH_INTENTS):
            return self._search_decision(message)

        if _is_knowledge_question(message) and context.knowledge:
            return LLMDecision(
                reply=self._answer_from_knowledge(context.knowledge[0]),
                used_knowledge=True,
            )

        missing = lead.missing_for_creation()
        if not missing:
            return LLMDecision(
                tool_name="create_lead",
                tool_arguments=self._lead_arguments(lead),
            )

        fields_here = extract_lead_fields(message)
        knows_something = (
            lead.requirement or lead.business_type or lead.name
            or fields_here.requirement or fields_here.business_type
        )
        if not knows_something:
            # Opening turn with no extractable intent: greet and invite.
            return LLMDecision(
                reply=(
                    "Hello! I'm the Autom8r assistant. I can answer questions about "
                    "our communication automation products, or help you get started. "
                    "What would you like to automate?"
                )
            )
        return LLMDecision(reply=self._next_question(missing, lead))

    def _update_decision(self, message: str, lead: ExtractedLead) -> LLMDecision:
        """'update my city to Mumbai' -> update_lead(phone=..., city=...)."""
        phone = extract_phone(message) or lead.phone
        if not phone:
            return LLMDecision(
                reply="Sure — what's the phone number on your lead so I can find it?"
            )
        fields = extract_lead_fields(message)
        args: ToolArguments = {"phone": phone}
        for attr in (
            "email", "city", "business_type", "budget", "requirement",
            "timeline", "monthly_queries",
        ):
            value = getattr(fields, attr)
            if value is not None:
                args[attr] = value
        if len(args) == 1:
            return LLMDecision(
                reply=(
                    "What would you like me to update? For example: "
                    "'update my city to Mumbai'."
                )
            )
        return LLMDecision(tool_name="update_lead", tool_arguments=args)

    def _search_decision(self, message: str) -> LLMDecision:
        """'find lead 9876543210' / 'search Rahul' -> search_lead(query)."""
        phone = extract_phone(message)
        if phone:
            return LLMDecision(tool_name="search_lead", tool_arguments={"query": phone})
        cleaned = _SEARCH_STOPWORDS.sub("", message.lower()).strip(" .?,")
        if not cleaned:
            return LLMDecision(reply="Sure — who or what number should I look up?")
        return LLMDecision(tool_name="search_lead", tool_arguments={"query": cleaned})

    def _answer_from_knowledge(self, top: RetrievalResult) -> str:
        """Ground the reply in the best retrieved chunk (source of truth)."""
        lines = top.chunk.split("\n")
        # Chunks are split on '## ' headings, so line 1 is the section title.
        body_lines = lines[1:] if len(lines) > 1 else lines
        body = " ".join(" ".join(body_lines).split())[:600]
        return (
            f"Based on our documentation ({top.document}): {body} "
            "Is there anything else you'd like to know?"
        )

    def _lead_arguments(self, lead: ExtractedLead) -> ToolArguments:
        """Map extracted fields to create_lead tool arguments."""
        args: ToolArguments = {
            "name": lead.name or "",
            "phone": lead.phone or "",
            "source": "chat",
        }
        if lead.email:
            args["email"] = lead.email
        if lead.city:
            args["city"] = lead.city
        if lead.business_type:
            args["business_type"] = lead.business_type
        if lead.budget:
            args["budget"] = lead.budget
        if lead.requirement:
            args["requirement"] = lead.requirement
        if lead.timeline:
            args["timeline"] = lead.timeline
        if lead.monthly_queries is not None:
            args["monthly_queries"] = lead.monthly_queries
        return args

    def _next_question(self, missing: list[str], lead: ExtractedLead) -> str:
        """Ask for the next missing piece, in a natural order."""
        if not lead.business_type:
            return "Absolutely, I can help with that. What type of business do you operate?"
        if lead.monthly_queries is None:
            return (
                "Thanks! Approximately how many customer enquiries do you "
                "receive per month?"
            )
        if "name" in missing or "phone" in missing:
            return (
                "Understood. Could you share your name and phone number so I "
                "can record your requirement?"
            )
        return "Could you tell me a bit more about what you'd like to automate?"


class OpenAILLMService:
    """Live mode: any OpenAI-compatible chat-completions endpoint.

    ``LLM_BASE_URL`` makes this work with OpenAI, OpenRouter, a local
    Ollama/vLLM server, or a CPaaS-hosted gateway — one SDK, many providers.
    """

    def __init__(self, settings: Settings) -> None:
        self._model = settings.llm_model or "gpt-4o-mini"
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
        )

    @property
    def mode(self) -> str:
        return "live"

    def create_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam],
    ) -> JSONValue:
        """One chat-completion call; the agent loop interprets the result."""
        logger.info("llm call start: model=%s messages=%d", self._model, len(messages))
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        logger.info("llm call end: model=%s", self._model)
        return json.loads(response.model_dump_json())


def build_llm_service(settings: Settings) -> LLMService | OpenAILLMService:
    """Factory: live when enabled+keyed, deterministic mock otherwise."""
    if settings.llm_mode == "live":
        logger.info("LLM mode: LIVE (model=%s)", settings.llm_model)
        return OpenAILLMService(settings)
    logger.info("LLM mode: MOCK (set LLM_ENABLED=true + LLM_API_KEY for live)")
    return MockLLMService()


def accumulate_extraction(message: str, history: list[ChatMessage]) -> ExtractedLead:
    """Re-derive accumulated lead fields from the whole conversation.

    The server is stateless, so each turn re-extracts from every user
    message in order and merges — cheap at demo scale, and context questions
    ('About 500.' after a volume question) resolve correctly.
    """
    accumulated = ExtractedLead()
    last_assistant = ""
    for turn in [*history, ChatMessage(role="user", content=message)]:
        if turn.role == "assistant":
            last_assistant = turn.content.lower()
            continue
        fields = extract_lead_fields(turn.content)
        accumulated = accumulated.merge(fields)
        accumulated = _apply_question_context(turn.content, last_assistant, accumulated)
    return accumulated


def _apply_question_context(
    text: str, last_assistant: str, lead: ExtractedLead
) -> ExtractedLead:
    """Interpret short answers using the question the assistant just asked."""
    from dataclasses import replace

    if "type of business" in last_assistant and lead.business_type is None:
        phrase = extract_business_type(text) or _short_phrase(text)
        if phrase:
            lead = replace(lead, business_type=phrase)
    if "how many" in last_assistant and lead.monthly_queries is None:
        number = extract_monthly_queries(text) or extract_bare_number(text)
        if number is not None:
            lead = replace(lead, monthly_queries=number)
    if "name and phone" in last_assistant and (lead.name is None or lead.phone is None):
        name, phone = extract_name_phone_pair(text)
        if name and lead.name is None:
            lead = replace(lead, name=name)
        if phone and lead.phone is None:
            lead = replace(lead, phone=phone)
    return lead
