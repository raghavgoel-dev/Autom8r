"""Shared response envelopes.

Every error the API returns has the same JSON shape, so the frontend (and
an interviewer reading the network tab) sees one predictable contract:

    {"success": false, "error": {"code": "LEAD_NOT_FOUND", "message": "..."}}
"""
from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    """Machine-readable error code + human-readable message."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope returned by exception handlers."""

    model_config = ConfigDict(frozen=True)

    success: bool = False
    error: ErrorBody
