"""Input validation helpers.

Every function either returns a cleaned/normalised value or raises
``ValidationError`` with a human-readable message that the GUI can show directly.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
MAX_TITLE_LEN = 100
MAX_CONTENT_LEN = 20_000
CATEGORY_PATTERN = re.compile(r"^[A-Za-z0-9 _&\-]{1,30}$")


class ValidationError(ValueError):
    """Raised when user supplied data is not acceptable."""


def validate_date(value: str, allow_future: bool = False) -> date:
    """Parse ``YYYY-MM-DD`` and return a ``date``."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Date is required (format YYYY-MM-DD).")
    try:
        parsed = datetime.strptime(value.strip(), DATE_FORMAT).date()
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid date. Use YYYY-MM-DD.") from None
    if not allow_future and parsed > date.today():
        raise ValidationError("Date cannot be in the future.")
    return parsed


def validate_optional_date(value: Optional[str]) -> Optional[date]:
    """Like :func:`validate_date` but an empty value returns ``None`` (used by filters)."""
    if value is None or not str(value).strip():
        return None
    return validate_date(value, allow_future=True)


def validate_time(value: str) -> str:
    """Validate ``HH:MM`` (24h) and return it zero-padded."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Time is required (format HH:MM, 24-hour).")
    try:
        parsed = datetime.strptime(value.strip(), TIME_FORMAT)
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid time. Use HH:MM (24-hour).") from None
    return parsed.strftime(TIME_FORMAT)


def validate_category(value: str) -> str:
    """Categories: 1-30 chars of letters, digits, space, ``_``, ``&`` or ``-``."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError("Category is required.")
    if not CATEGORY_PATTERN.match(cleaned):
        raise ValidationError(
            "Category must be 1-30 characters: letters, digits, spaces, '_', '&' or '-'."
        )
    return cleaned.title()


def validate_title(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError("Title is required.")
    if len(cleaned) > MAX_TITLE_LEN:
        raise ValidationError(f"Title must be at most {MAX_TITLE_LEN} characters.")
    return cleaned


def validate_content(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError("Entry text cannot be empty.")
    if len(cleaned) > MAX_CONTENT_LEN:
        raise ValidationError(f"Entry text must be at most {MAX_CONTENT_LEN} characters.")
    return cleaned


def validate_mood(value) -> Optional[int]:
    """Mood is optional: blank/None -> ``None``; otherwise an integer 1..5."""
    if value is None or str(value).strip() == "":
        return None
    try:
        mood = int(str(value).strip())
    except ValueError:
        raise ValidationError("Mood must be a whole number from 1 to 5.") from None
    if not 1 <= mood <= 5:
        raise ValidationError("Mood must be between 1 (low) and 5 (high).")
    return mood
