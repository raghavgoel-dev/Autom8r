"""Webhook event ledger — how we make webhook processing idempotent.

External systems may deliver the same event twice (retries are normal).
We record each processed ``event_id`` and acknowledge repeats as duplicates
instead of creating a second lead.
"""  # noqa: MUTABLE_OK — ORM rows are mutable by design.
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WebhookEventRecord(Base):
    """One row per processed webhook event_id."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50))
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
