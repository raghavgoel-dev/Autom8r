"""Lead-management MCP tools.

These are the business capabilities the AI agent can invoke. Every tool has
a precise description (tool descriptions are how a model decides WHEN to
call) and safety annotations (readOnlyHint etc.) per MCP conventions.

Shared scoring comes from the backend package (imported via repo root on
sys.path, set up in server.py) so REST-created and MCP-created leads score
identically.
"""
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict

from backend.app.services.scoring import (
    LeadSignals,
    compute_lead_score,
    priority_for_score,
)
from mcp_server.db import LeadStore


class LeadResult(BaseModel):
    """A lead record as tools return it (matches the REST LeadOut shape)."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    phone: str
    email: str | None
    city: str | None
    business_type: str | None
    budget: str | None
    requirement: str | None
    timeline: str | None
    monthly_queries: int | None
    lead_score: int
    priority: str
    status: str
    source: str
    created_at: str
    updated_at: str


class SearchResult(BaseModel):
    """Outcome of a lead search."""

    model_config = ConfigDict(frozen=True)

    count: int
    leads: list[LeadResult]


def _score(fields: dict[str, object]) -> tuple[int, str]:
    """Compute (score, priority) from raw tool arguments."""
    signals = LeadSignals(
        phone=_as_str(fields.get("phone")),
        email=_as_str(fields.get("email")),
        requirement=_as_str(fields.get("requirement")),
        business_type=_as_str(fields.get("business_type")),
        city=_as_str(fields.get("city")),
        timeline=_as_str(fields.get("timeline")),
        monthly_queries=fields.get("monthly_queries")
        if isinstance(fields.get("monthly_queries"), int)
        else None,
    )
    score = compute_lead_score(signals)
    return score, priority_for_score(score)


def _as_str(value: object) -> str | None:
    """Narrow an untyped field to str|None for the scoring signals."""
    return value if isinstance(value, str) else None


def register_lead_tools(mcp: MCPServer, store: LeadStore) -> None:
    """Attach the three lead tools to the server (keeps server.py tiny)."""

    @mcp.tool(
        name="create_lead",
        title="Create Lead",
        description=(
            "Create a NEW sales lead in the CRM database after collecting the "
            "customer's details. Requires name and phone; include any known "
            "business_type, requirement, city, budget, timeline, and "
            "monthly_queries. Do NOT use for leads that already exist — use "
            "update_lead for those."
        ),
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False,
            idempotent_hint=False, open_world_hint=False,
        ),
    )
    def create_lead(
        name: str,
        phone: str,
        email: str | None = None,
        city: str | None = None,
        business_type: str | None = None,
        budget: str | None = None,
        requirement: str | None = None,
        timeline: str | None = None,
        monthly_queries: int | None = None,
        source: str = "chat",
    ) -> LeadResult:
        """Create a lead; the demonstration score is computed server-side."""
        fields: dict[str, object] = {
            "name": name, "phone": phone, "email": email, "city": city,
            "business_type": business_type, "budget": budget,
            "requirement": requirement, "timeline": timeline,
            "monthly_queries": monthly_queries, "source": source,
        }
        score, priority = _score(fields)
        row = store.create_lead(fields, score, priority)
        return LeadResult.model_validate(row)

    @mcp.tool(
        name="search_lead",
        title="Search Leads",
        description=(
            "Look up EXISTING leads by phone number or name fragment. Use "
            "this to check whether a customer already has a record before "
            "creating one, or to answer 'do you have my details?' questions. "
            "Read-only: never modifies data."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False,
            idempotent_hint=True, open_world_hint=False,
        ),
    )
    def search_lead(query: str) -> SearchResult:
        """Return up to 20 leads whose phone or name contains the query."""
        rows = store.search_leads(query)
        leads = [LeadResult.model_validate(row) for row in rows]
        return SearchResult(count=len(leads), leads=leads)

    @mcp.tool(
        name="update_lead",
        title="Update Lead",
        description=(
            "Update fields on an EXISTING lead, located by phone number. "
            "Use when a customer corrects or adds details (city, email, "
            "timeline, budget, ...). Raises an error when no lead with that "
            "phone exists — search first if unsure."
        ),
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False,
            idempotent_hint=True, open_world_hint=False,
        ),
    )
    def update_lead(
        phone: str,
        email: str | None = None,
        city: str | None = None,
        business_type: str | None = None,
        budget: str | None = None,
        requirement: str | None = None,
        timeline: str | None = None,
        monthly_queries: int | None = None,
    ) -> LeadResult:
        """Update one lead found by phone; recompute its demonstration score."""
        updates: dict[str, object] = {
            key: value
            for key, value in {
                "email": email, "city": city, "business_type": business_type,
                "budget": budget, "requirement": requirement,
                "timeline": timeline, "monthly_queries": monthly_queries,
            }.items()
            if value is not None
        }
        existing = store.search_leads(phone, limit=1)
        if not existing or existing[0]["phone"] != phone:
            raise ValueError(f"no lead found with phone {phone}")
        merged: dict[str, object] = {**existing[0], **updates, "phone": phone}
        score, priority = _score(merged)
        row = store.update_lead(phone, updates, score, priority)
        if row is None:
            raise ValueError(f"no lead found with phone {phone}")
        return LeadResult.model_validate(row)
