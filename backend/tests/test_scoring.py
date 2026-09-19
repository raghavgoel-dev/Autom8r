"""Scoring + extraction tests: the deterministic qualification engine."""
import pytest

from app.services.extraction import (
    extract_lead_fields,
    extract_name_phone_pair,
    extract_phone,
)
from app.services.scoring import (
    LeadSignals,
    compute_lead_score,
    priority_for_score,
    timeline_within_3_months,
)


def test_empty_signals_score_zero() -> None:
    """Given no known fields, the score is 0 and priority low."""
    assert compute_lead_score(LeadSignals()) == 0
    assert priority_for_score(0) == "low"


def test_full_signals_score_100_and_clamp() -> None:
    """Given every signal present, the score clamps at 100 (not 105)."""
    signals = LeadSignals(
        phone="9876543210", email="a@b.com", requirement="whatsapp automation",
        business_type="real estate", city="Mumbai", timeline="ASAP",
        monthly_queries=500,
    )
    assert compute_lead_score(signals) == 100
    assert priority_for_score(100) == "high"


def test_spec_example_conversation_scores_65_medium() -> None:
    """Given the Rahul conversation fields (phone, requirement, business
    type, high volume)
    When scored per the section-15 model
    Then 20+15+15+15 = 65 -> medium (the section-4 '85' assumed more fields)."""
    signals = LeadSignals(
        phone="9876543210", requirement="WhatsApp customer support automation",
        business_type="real estate", monthly_queries=500,
    )
    assert compute_lead_score(signals) == 65
    assert priority_for_score(65) == "medium"


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0, "low"), (39, "low"), (40, "medium"), (69, "medium"), (70, "high"), (100, "high")],
)
def test_priority_band_edges(score: int, expected: str) -> None:
    """Given boundary scores, priority bands are exact."""
    assert priority_for_score(score) == expected


@pytest.mark.parametrize(
    ("timeline", "expected"),
    [
        ("ASAP", True),
        ("within 2 months", True),
        ("next month", True),
        ("immediately", True),
        ("next year", False),
        ("within 6 months", False),
        (None, False),
        ("", False),
    ],
)
def test_timeline_within_3_months(timeline: str | None, expected: bool) -> None:
    """Given various timeline phrases, urgency detection is deterministic."""
    assert timeline_within_3_months(timeline) is expected


def test_extract_phone_normalizes_formatting() -> None:
    """Given a formatted phone string, digits are extracted."""
    assert extract_phone("call me at +91 98765-43210") == "919876543210"


def test_extract_name_phone_pair_compact_answer() -> None:
    """Given 'Rahul, 9876543210.', both fields are extracted."""
    name, phone = extract_name_phone_pair("Rahul, 9876543210.")
    assert name == "Rahul"
    assert phone == "9876543210"


def test_extract_requirement_from_interest_phrase() -> None:
    """Given the spec's opening turn, the requirement is captured."""
    fields = extract_lead_fields(
        "I want to know about your service and I am interested in "
        "automating WhatsApp customer support."
    )
    assert fields.requirement is not None
    assert "WhatsApp customer support" in fields.requirement


def test_extract_business_type_keyword() -> None:
    """Given 'Real estate.', the business type keyword is found."""
    assert extract_lead_fields("Real estate.").business_type == "real estate"


def test_extract_email_and_city() -> None:
    """Given an email and a known city, both are extracted."""
    fields = extract_lead_fields("I am Priya from Bengaluru, priya@example.com")
    assert fields.email == "priya@example.com"
    assert fields.city == "Bengaluru"
