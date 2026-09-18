"""Input validation helpers shared by schema validators.

Keep these dependency-free (stdlib only) so any layer can import them.
"""
import re

_PHONE_DIGITS = re.compile(r"\D+")


class PhoneValidationError(ValueError):
    """Raised when a string cannot be a real phone number."""


def normalize_phone(raw: str) -> str:
    """Return the digits-only form of a phone number, or raise.

    Accepts common formatting ('+91 98765-43210' -> '919876543210') and
    enforces a plausible length so obvious garbage fails with HTTP 422.
    """
    digits = _PHONE_DIGITS.sub("", raw)
    if not 7 <= len(digits) <= 15:
        raise PhoneValidationError("phone must contain 7 to 15 digits")
    return digits
