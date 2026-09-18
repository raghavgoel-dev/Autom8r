"""Lead CRUD endpoints — the REST teaching surface of Autom8r.

Demonstrates the core HTTP verbs with correct status codes:
  GET    /api/v1/leads          200 list (query params = filters)
  GET    /api/v1/leads/{id}     200 one / 404 missing
  POST   /api/v1/leads          201 created (body validated -> 422 on junk)
  PATCH  /api/v1/leads/{id}     200 updated (partial body)
  DELETE /api/v1/leads/{id}     204 no content
"""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.lead import (
    LeadCreate,
    LeadListResponse,
    LeadOut,
    LeadResponse,
    LeadUpdate,
)
from app.services import lead_service
from app.services.sheets_service import SheetsService

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


def _sheets() -> SheetsService:
    """Dependency seam for the optional Sheets adapter (tests override it)."""
    from app.config import settings

    return SheetsService(settings)


@router.get("", response_model=LeadListResponse)
def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    city: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    """List leads, newest first, with optional exact-match filters."""
    leads = lead_service.list_leads(
        db, status=status_filter, priority=priority, city=city, phone=phone,
        limit=limit, offset=offset,
    )
    return LeadListResponse(
        count=len(leads), leads=[LeadOut.model_validate(lead) for lead in leads]
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadResponse:
    """Fetch one lead by id (404 when missing)."""
    lead = lead_service.get_lead(db, lead_id)
    return LeadResponse(lead=LeadOut.model_validate(lead))


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    sheets: SheetsService = Depends(_sheets),
) -> LeadResponse:
    """Create a lead; score and priority are computed server-side."""
    lead = lead_service.create_lead(db, payload)
    sheets.sync_lead_created(lead)  # best-effort, no-op unless configured
    return LeadResponse(lead=LeadOut.model_validate(lead))


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)
) -> LeadResponse:
    """Partially update a lead (only the fields present in the body)."""
    lead = lead_service.update_lead(db, lead_id, payload)
    return LeadResponse(lead=LeadOut.model_validate(lead))


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a lead. 204 means 'done, and there is nothing to show you'."""
    lead_service.delete_lead(db, lead_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
