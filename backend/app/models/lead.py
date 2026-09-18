"""Lead ORM model — the central table of Autom8r.

SQLAlchemy 2.0 style: ``Mapped[...]`` annotations + ``mapped_column``.
The same table is written by three surfaces: the REST API, the webhook
receiver, and the MCP server tools (via raw SQL — see mcp_server/).
"""  # noqa: MUTABLE_OK — ORM rows are mutable by design (SQLAlchemy contract).
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

# The only two controlled vocabularies in the schema.
LEAD_STATUSES: tuple[str, ...] = ("new", "contacted", "qualified", "converted", "lost")
LEAD_PRIORITIES: tuple[str, ...] = ("low", "medium", "high")


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp for created_at/updated_at."""
    return datetime.now(timezone.utc)


class Lead(Base):
    """A sales lead captured from chat, the REST API, or a webhook."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    city: Mapped[str | None] = mapped_column(String(120))
    business_type: Mapped[str | None] = mapped_column(String(120))
    budget: Mapped[str | None] = mapped_column(String(120))
    requirement: Mapped[str | None] = mapped_column(Text)
    timeline: Mapped[str | None] = mapped_column(String(120))
    monthly_queries: Mapped[int | None] = mapped_column(Integer)
    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(10), default="low", index=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    source: Mapped[str] = mapped_column(String(50), default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
