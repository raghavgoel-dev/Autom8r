"""Admin endpoints — protected by the demo Bearer token.

  GET /api/v1/admin/stats         aggregate lead counts
  GET /api/v1/admin/recent-leads  newest leads
  GET /api/v1/admin/tools         live MCP tool discovery (503 when MCP down)
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.lead import LeadListResponse, LeadOut
from app.services import lead_service
from app.utils.security import require_admin

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)) -> dict[str, object]:
    """Aggregate lead metrics for the dashboard."""
    stats = lead_service.get_stats(db)
    return {
        "success": True,
        "stats": {
            "total_leads": stats.total_leads,
            "new_leads": stats.new_leads,
            "qualified_leads": stats.qualified_leads,
            "high_priority_leads": stats.high_priority_leads,
            "medium_priority_leads": stats.medium_priority_leads,
            "low_priority_leads": stats.low_priority_leads,
        },
    }


@router.get("/recent-leads", response_model=LeadListResponse)
def get_recent_leads(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    """Newest leads for the admin panel."""
    leads = lead_service.recent_leads(db, limit=limit)
    return LeadListResponse(
        count=len(leads), leads=[LeadOut.model_validate(lead) for lead in leads]
    )


@router.get("/tools")
async def get_tools(request: Request) -> dict[str, object]:
    """Discover tools from the MCP server (live proof of MCP connectivity).

    Raises MCPUnavailableError (-> 503 envelope) when the server is down.
    """
    mcp = request.app.state.mcp
    tools = await mcp.list_tools()
    return {
        "success": True,
        "mcp_available": True,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "read_only": tool.read_only,
            }
            for tool in tools
        ],
    }
