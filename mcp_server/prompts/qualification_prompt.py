"""The lead-qualification prompt, exposed over MCP.

MCP prompts are reusable prompt templates a CLIENT can fetch. This mirrors
backend/app/prompts/qualification_prompt.txt so an external MCP host (Claude
Desktop, an IDE, another agent) could pull the same qualification guidance
straight from the server.
"""
from mcp.server.mcpserver import MCPServer

_PROMPT_TEXT = """You are qualifying a sales lead for a communications-automation company.

Collect, in a natural conversational order:
  business_type    - what kind of business they run
  monthly_queries  - approximate customer enquiries per month
  name             - the customer's name
  phone            - phone number
Also useful when offered: email, city, budget, timeline.

Rules:
- Ask for at most one or two missing pieces per turn.
- Never invent lead data; only record what the customer states.
- When name, phone, and a requirement or business type are known, call the
  create_lead tool.
- Do not mention scores or internal fields to the customer.
"""


def register_prompts(mcp: MCPServer) -> None:
    """Attach the lead_qualification_prompt to the server."""

    @mcp.prompt(
        name="lead_qualification_prompt",
        title="Lead Qualification",
        description="Guide an assistant through collecting and recording a sales lead.",
    )
    def lead_qualification_prompt() -> str:
        """Return the qualification instructions as a reusable prompt."""
        return _PROMPT_TEXT
