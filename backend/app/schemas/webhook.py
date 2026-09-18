"""Webhook schemas.

A webhook is the inverse of an API call: instead of us calling an external
system, the external system calls *our* endpoint when an event happens.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.lead import LeadOut
from app.utils.validators import normalize_phone


class WebhookLeadData(BaseModel):
    """The ``data`` object of a lead.created webhook event."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    business_type: str | None = Field(default=None, max_length=120)
    requirement: str | None = None
    monthly_queries: int | None = Field(default=None, ge=0)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str) -> str:
        """Normalize to digits (same rule as the REST API)."""
        return normalize_phone(value)


class WebhookEvent(BaseModel):
    """POST /api/v1/webhooks/lead payload.

    ``event_id`` enables idempotent processing: a redelivered event with a
    known id is acknowledged as a duplicate instead of creating a second lead.
    """

    model_config = ConfigDict(frozen=True)

    event: Literal["lead.created"]
    source: str = Field(min_length=1, max_length=50)
    timestamp: datetime | None = None
    event_id: str | None = Field(default=None, max_length=120)
    data: WebhookLeadData


class WebhookResponse(BaseModel):
    """Webhook acknowledgement envelope."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    duplicate: bool = False
    lead: LeadOut | None = None
    message: str
