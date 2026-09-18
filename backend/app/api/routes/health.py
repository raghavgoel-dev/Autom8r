"""GET /health — liveness probe.

Load balancers, Cloud Run, and curious interviewers all hit this first.
It also reports the LLM mode so the UI can badge "Mock LLM" honestly.
"""
from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return service liveness and the active LLM mode."""
    return {
        "status": "ok",
        "app": "autom8r",
        "version": "0.1.0",
        "llm_mode": settings.llm_mode,
    }
