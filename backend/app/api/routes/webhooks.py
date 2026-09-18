"""POST /api/v1/webhooks/lead — inbound event receiver.

API call:   "I call your API."
Webhook:    "Your system calls MY endpoint when an event occurs."

Secured with a shared secret header (X-Webhook-Secret) and made idempotent
with an event ledger: a redelivered event_id is acknowledged as a duplicate
instead of creating a second lead.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.webhook_event import WebhookEventRecord
from app.schemas.lead import LeadCreate, LeadOut
from app.schemas.webhook import WebhookEvent, WebhookResponse
from app.services import lead_service
from app.services.sheets_service import SheetsService
from app.utils.security import verify_webhook_secret

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
    dependencies=[Depends(verify_webhook_secret)],
)


def _sheets() -> SheetsService:
    """Same optional-sync seam as the leads router."""
    from app.config import settings

    return SheetsService(settings)


@router.post("/lead", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def receive_lead_event(
    payload: WebhookEvent,
    response: Response,
    db: Session = Depends(get_db),
    sheets: SheetsService = Depends(_sheets),
) -> WebhookResponse:
    """Ingest a lead.created event; dedupe on event_id when provided."""
    logger.info("webhook received: event=%s source=%s", payload.event, payload.source)

    if payload.event_id:
        seen = db.scalar(
            select(WebhookEventRecord).where(
                WebhookEventRecord.event_id == payload.event_id
            )
        )
        if seen is not None:
            response.status_code = status.HTTP_200_OK
            return WebhookResponse(
                duplicate=True, lead=None, message="Duplicate event ignored"
            )

    lead = lead_service.create_lead(
        db,
        LeadCreate(
            name=payload.data.name,
            phone=payload.data.phone,
            email=payload.data.email,
            city=payload.data.city,
            business_type=payload.data.business_type,
            requirement=payload.data.requirement,
            monthly_queries=payload.data.monthly_queries,
            source=payload.source,
        ),
    )
    if payload.event_id:
        db.add(WebhookEventRecord(event_id=payload.event_id, source=payload.source))
        db.commit()
    sheets.sync_lead_created(lead)
    return WebhookResponse(
        lead=LeadOut.model_validate(lead), message="Lead created from webhook"
    )
