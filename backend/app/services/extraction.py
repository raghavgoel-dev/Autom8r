"""Rule-based lead-field extraction from conversation text.

This is the deterministic engine behind MockLLMService and a safety net for
live mode: it pulls structured fields (name, phone, business type, ...) out
of free-text user turns using explicit, explainable patterns — no ML model,
no network, fully testable.

Pure stdlib on purpose (same sharing story as scoring.py).
"""
import re
from dataclasses import dataclass, replace

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RUN_RE = re.compile(r"\+?\d[\d\s\-()]{5,18}\d")
_BARE_NUMBER_RE = re.compile(r"\b(\d{2,6})\b")
_BUDGET_RE = re.compile(
    r"(?:₹|rs\.?|inr|\$|usd)\s?[\d,]+(?:\s?(?:k|lakh|lac|crore|per month|/month|monthly))?"
    r"|[\d,]+\s?(?:k|lakh|lac)\b",
    re.IGNORECASE,
)

_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"my name is ([A-Za-z][A-Za-z .]{1,40})", re.IGNORECASE),
    re.compile(r"\bi am ([A-Za-z][A-Za-z .]{1,40})", re.IGNORECASE),
    re.compile(r"\bi'm ([A-Za-z][A-Za-z .]{1,40})", re.IGNORECASE),
    re.compile(r"this is ([A-Za-z][A-Za-z .]{1,40})", re.IGNORECASE),
)

# Keyword vocabulary for business types (longest match wins).
_BUSINESS_TYPES: tuple[str, ...] = (
    "real estate",
    "e-commerce",
    "ecommerce",
    "healthcare",
    "education",
    "edtech",
    "restaurant",
    "retail",
    "finance",
    "fintech",
    "insurance",
    "banking",
    "travel",
    "logistics",
    "manufacturing",
    "hospitality",
    "hotel",
    "pharmacy",
    "automobile",
    "salon",
    "gym",
    "fitness",
    "software",
    "saas",
    "technology",
    "consulting",
    "legal",
    "clinic",
    "hospital",
    "jewellery",
    "jewelry",
)

_REQUIREMENT_TRIGGERS: tuple[str, ...] = (
    "interested in",
    "looking for",
    "looking to",
    "want to",
    "wants to",
    "need to",
    "need",
    "want",
    "automate",
    "automating",
    "automation",
)

_TIMELINE_RE = re.compile(
    r"(asap|immediately|urgent(?:ly)?|right away|soon|this month|next month|"
    r"this quarter|within \d+ (?:days?|weeks?|months?)|in \d+ (?:days?|weeks?|months?)|"
    r"\d+ (?:days?|weeks?|months?))",
    re.IGNORECASE,
)

_QUERY_VOLUME_RE = re.compile(
    r"(\d{2,6})\s*(?:customer\s)?(?:enquiries|inquiries|queries|messages|chats|leads|calls)"
    r"(?:\s*(?:per|a|each|every)\s*(?:day|week|month))?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExtractedLead:
    """Structured fields pulled from conversation text (all optional)."""

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    business_type: str | None = None
    budget: str | None = None
    requirement: str | None = None
    timeline: str | None = None
    monthly_queries: int | None = None

    def merge(self, newer: "ExtractedLead") -> "ExtractedLead":
        """Accumulate across turns: newer non-None values win."""
        return replace(
            self,
            name=newer.name or self.name,
            phone=newer.phone or self.phone,
            email=newer.email or self.email,
            city=newer.city or self.city,
            business_type=newer.business_type or self.business_type,
            budget=newer.budget or self.budget,
            requirement=newer.requirement or self.requirement,
            timeline=newer.timeline or self.timeline,
            monthly_queries=newer.monthly_queries
            if newer.monthly_queries is not None
            else self.monthly_queries,
        )

    def missing_for_creation(self) -> list[str]:
        """Fields still needed before a lead is worth creating."""
        missing: list[str] = []
        if not self.name:
            missing.append("name")
        if not self.phone:
            missing.append("phone")
        if not (self.requirement or self.business_type):
            missing.append("requirement")
        return missing


def extract_email(text: str) -> str | None:
    """First email address in the text, if any."""
    match = _EMAIL_RE.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    """First plausible phone number, normalized to digits."""
    for match in _PHONE_RUN_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 7 <= len(digits) <= 15:
            return digits
    return None


def extract_name(text: str) -> str | None:
    """Name from an explicit introduction pattern ('my name is ...')."""
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            # Cut trailing words that are clearly not part of a name.
            candidate = re.split(r"[,.!?\n]|\s+and\s+|\s+from\s+", match.group(1))[0].strip()
            if candidate:
                return candidate
    return None


def extract_name_phone_pair(text: str) -> tuple[str | None, str | None]:
    """Handle the compact 'Rahul, 9876543210' answer shape."""
    for match in _PHONE_RUN_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if not 7 <= len(digits) <= 15:
            continue
        name_part = text[: match.start()].strip().strip(",").strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z .]{0,40}", name_part):
            return (name_part or None), digits
        return None, digits
    return None, None


def extract_business_type(text: str) -> str | None:
    """Longest matching known business-type keyword."""
    lowered = text.lower()
    for business in _BUSINESS_TYPES:  # already ordered longest-first-ish
        if business in lowered:
            return business
    return None


def extract_monthly_queries(text: str) -> int | None:
    """Volume like '500 enquiries per month' / 'about 2000 messages'."""
    match = _QUERY_VOLUME_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def extract_bare_number(text: str) -> int | None:
    """A standalone number ('About 500.') — meaning depends on context."""
    match = _BARE_NUMBER_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def extract_budget(text: str) -> str | None:
    """A currency amount or '50k' style budget mention."""
    match = _BUDGET_RE.search(text)
    return match.group(0).strip() if match else None


def extract_timeline(text: str) -> str | None:
    """A timeline phrase ('within 2 months', 'ASAP', ...)."""
    match = _TIMELINE_RE.search(text)
    return match.group(0).strip() if match else None


def extract_requirement(text: str) -> str | None:
    """What the customer wants, e.g. 'automating WhatsApp customer support'."""
    lowered = text.lower()
    for trigger in _REQUIREMENT_TRIGGERS:
        idx = lowered.find(trigger)
        if idx == -1:
            continue
        phrase = text[idx + len(trigger):].strip().strip(".!").strip()
        if not phrase:
            continue
        # Trim to the first sentence/clause — requirements are short.
        phrase = re.split(r"[.!?\n]", phrase)[0].strip()
        if not phrase:
            continue
        if "automat" in phrase.lower() and "automation" not in phrase.lower():
            phrase = re.sub(r"\bautomating\b", "", phrase, flags=re.IGNORECASE).strip()
            phrase = f"{phrase} automation".strip()
        return phrase
    return None


def extract_lead_fields(text: str) -> ExtractedLead:
    """Run every extractor over one message and bundle the results."""
    name, phone = extract_name_phone_pair(text)
    return ExtractedLead(
        name=name or extract_name(text),
        phone=phone,
        email=extract_email(text),
        business_type=extract_business_type(text),
        budget=extract_budget(text),
        requirement=extract_requirement(text),
        timeline=extract_timeline(text),
        monthly_queries=extract_monthly_queries(text),
    )
