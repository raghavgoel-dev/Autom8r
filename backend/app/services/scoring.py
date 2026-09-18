"""Deterministic lead scoring — a DEMONSTRATION heuristic, not a sales model.

This module is intentionally pure stdlib: the MCP server process imports it
directly (``from backend.app.services.scoring import ...``) so both service
surfaces score leads identically with zero code duplication.

Scoring model (spec section 15):
    +20 phone present
    +10 email present
    +15 requirement clear
    +15 business type present
    +10 city present
    +15 timeline within 3 months
    +15 high-volume enquiry count (monthly_queries >= HIGH_VOLUME_THRESHOLD)
Clamped to 0..100. Priority bands: 0-39 low, 40-69 medium, 70-100 high.
"""
from dataclasses import dataclass

HIGH_VOLUME_THRESHOLD: int = 300

# Phrases that mean "the customer wants to start soon" (<= 3 months out).
_URGENT_TIMELINE_MARKERS: tuple[str, ...] = (
    "asap",
    "immediately",
    "urgent",
    "right away",
    "this month",
    "next month",
    "this quarter",
    "soon",
    "1 month",
    "2 month",
    "3 month",
    "one month",
    "two month",
    "three month",
    "1 week",
    "2 week",
    "3 week",
    "4 week",
    "one week",
    "two week",
    "three week",
)


@dataclass(frozen=True, slots=True)
class LeadSignals:
    """The presence/absence signals scoring consumes (no DB, no I/O)."""

    phone: str | None = None
    email: str | None = None
    requirement: str | None = None
    business_type: str | None = None
    city: str | None = None
    timeline: str | None = None
    monthly_queries: int | None = None


def timeline_within_3_months(timeline: str | None) -> bool:
    """True when free-text timeline implies starting within ~3 months."""
    if not timeline:
        return False
    text = timeline.strip().lower()
    return any(marker in text for marker in _URGENT_TIMELINE_MARKERS)


def compute_lead_score(signals: LeadSignals) -> int:
    """Sum the weighted signals and clamp to 0..100."""
    score = 0
    if signals.phone:
        score += 20
    if signals.email:
        score += 10
    if signals.requirement:
        score += 15
    if signals.business_type:
        score += 15
    if signals.city:
        score += 10
    if timeline_within_3_months(signals.timeline):
        score += 15
    if signals.monthly_queries is not None and signals.monthly_queries >= HIGH_VOLUME_THRESHOLD:
        score += 15
    return max(0, min(100, score))


def priority_for_score(score: int) -> str:
    """Map a 0..100 score to the low/medium/high priority bands."""
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"
