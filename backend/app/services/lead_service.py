"""Lead business logic: CRUD, search, stats, and scoring integration.

Routes stay thin; everything a lead can *do* lives here so the REST API,
the webhook receiver, and tests all share one implementation.
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate
from app.services.scoring import LeadSignals, compute_lead_score, priority_for_score
from app.utils.errors import LeadNotFoundError

logger = get_logger(__name__)

# Fields whose change can move the lead score.
_SCORING_FIELDS = (
    "phone", "email", "requirement", "business_type", "city", "timeline",
    "monthly_queries",
)


@dataclass(frozen=True, slots=True)
class LeadStats:
    """Aggregate counts for the admin dashboard."""

    total_leads: int
    new_leads: int
    qualified_leads: int
    high_priority_leads: int
    medium_priority_leads: int
    low_priority_leads: int


def _signals_from(lead: Lead) -> LeadSignals:
    """Build scoring signals from an ORM row."""
    return LeadSignals(
        phone=lead.phone, email=lead.email, requirement=lead.requirement,
        business_type=lead.business_type, city=lead.city,
        timeline=lead.timeline, monthly_queries=lead.monthly_queries,
    )


def _apply_score(lead: Lead) -> None:
    """Recompute score + priority on a row from its current fields."""
    score = compute_lead_score(_signals_from(lead))
    lead.lead_score = score
    lead.priority = priority_for_score(score)


def create_lead(db: Session, data: LeadCreate, *, source: str | None = None) -> Lead:
    """Create a lead, computing its demonstration score and priority."""
    lead = Lead(
        name=data.name, phone=data.phone, email=data.email, city=data.city,
        business_type=data.business_type, budget=data.budget,
        requirement=data.requirement, timeline=data.timeline,
        monthly_queries=data.monthly_queries,
        source=source or data.source,
    )
    _apply_score(lead)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info("lead created: id=%d source=%s score=%d", lead.id, lead.source, lead.lead_score)
    return lead


def get_lead(db: Session, lead_id: int) -> Lead:
    """Fetch one lead or raise LeadNotFoundError (-> HTTP 404)."""
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFoundError(f"Lead {lead_id} not found")
    return lead


def list_leads(
    db: Session,
    *,
    status: str | None = None,
    priority: str | None = None,
    city: str | None = None,
    phone: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Lead]:
    """List leads with optional exact-match filters, newest first."""
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Lead.status == status)
    if priority:
        stmt = stmt.where(Lead.priority == priority)
    if city:
        stmt = stmt.where(Lead.city == city)
    if phone:
        stmt = stmt.where(Lead.phone == phone)
    return list(db.scalars(stmt).all())


def search_leads(db: Session, query: str) -> list[Lead]:
    """Free-text search over phone and name (used by the MCP search tool's
    REST counterpart and handy for debugging)."""
    pattern = f"%{query.strip()}%"
    stmt = (
        select(Lead)
        .where((Lead.phone.like(pattern)) | (Lead.name.like(pattern)))
        .order_by(Lead.created_at.desc())
        .limit(20)
    )
    return list(db.scalars(stmt).all())


def update_lead(db: Session, lead_id: int, data: LeadUpdate) -> Lead:
    """Apply a partial update; recompute score when a scoring field changed."""
    lead = get_lead(db, lead_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(lead, field, value)
    scoring_changed = any(field in _SCORING_FIELDS for field in changes)
    if scoring_changed:
        explicit_priority = "priority" in changes
        if explicit_priority:
            lead.lead_score = compute_lead_score(_signals_from(lead))
        else:
            _apply_score(lead)
    db.commit()
    db.refresh(lead)
    logger.info("lead updated: id=%d fields=%s", lead.id, sorted(changes))
    return lead


def delete_lead(db: Session, lead_id: int) -> None:
    """Delete a lead (404 when it does not exist)."""
    lead = get_lead(db, lead_id)
    db.delete(lead)
    db.commit()
    logger.info("lead deleted: id=%d", lead_id)


def recent_leads(db: Session, limit: int = 5) -> list[Lead]:
    """Newest leads for the admin panel."""
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def get_stats(db: Session) -> LeadStats:
    """Aggregate lead counts for GET /api/v1/admin/stats."""
    total = db.scalar(select(func.count(Lead.id))) or 0

    def count_where(column: object, value: str) -> int:
        return db.scalar(select(func.count(Lead.id)).where(column == value)) or 0

    return LeadStats(
        total_leads=total,
        new_leads=count_where(Lead.status, "new"),
        qualified_leads=count_where(Lead.status, "qualified"),
        high_priority_leads=count_where(Lead.priority, "high"),
        medium_priority_leads=count_where(Lead.priority, "medium"),
        low_priority_leads=count_where(Lead.priority, "low"),
    )
