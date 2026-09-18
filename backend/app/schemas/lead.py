"""Lead request/response schemas.

Pydantic v2 parses and validates untrusted JSON at the API boundary
("parse, don't validate"): route functions below never see a bad payload.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.lead import LEAD_PRIORITIES, LEAD_STATUSES
from app.utils.validators import normalize_phone

Priority = Literal["low", "medium", "high"]
Status = Literal["new", "contacted", "qualified", "converted", "lost"]


class LeadCreate(BaseModel):
    """Fields accepted when creating a lead via POST /api/v1/leads."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    business_type: str | None = Field(default=None, max_length=120)
    budget: str | None = Field(default=None, max_length=120)
    requirement: str | None = None
    timeline: str | None = Field(default=None, max_length=120)
    monthly_queries: int | None = Field(default=None, ge=0)
    source: str = Field(default="api", max_length=50)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str) -> str:
        """Normalize to digits and reject anything that is not a phone number."""
        return normalize_phone(value)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        """Reject whitespace-only names."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class LeadUpdate(BaseModel):
    """PATCH payload: every field optional; only provided fields change."""

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    business_type: str | None = Field(default=None, max_length=120)
    budget: str | None = Field(default=None, max_length=120)
    requirement: str | None = None
    timeline: str | None = Field(default=None, max_length=120)
    monthly_queries: int | None = Field(default=None, ge=0)
    status: Status | None = None
    priority: Priority | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        """Normalize phone when present; pass None through untouched."""
        return normalize_phone(value) if value is not None else None


class LeadOut(BaseModel):
    """Full lead record as returned to clients (mirrors the ORM row)."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

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
    created_at: datetime
    updated_at: datetime


class LeadResponse(BaseModel):
    """Single-lead success envelope."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    lead: LeadOut


class LeadListResponse(BaseModel):
    """Lead list success envelope."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    count: int
    leads: list[LeadOut]


# Re-export so routes can validate against the canonical vocabularies.
__all__ = [
    "LEAD_PRIORITIES",
    "LEAD_STATUSES",
    "LeadCreate",
    "LeadListResponse",
    "LeadOut",
    "LeadResponse",
    "LeadUpdate",
    "Priority",
    "Status",
]
