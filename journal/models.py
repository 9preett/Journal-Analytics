"""Core data structure: a single journal entry."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import validators as v


@dataclass
class Entry:
    """One journal entry. ``date`` is ISO ``YYYY-MM-DD`` and ``time`` is ``HH:MM``."""

    id: str
    date: str
    time: str
    category: str
    title: str
    content: str
    mood: Optional[int] = None

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Serialisable form (word_count is stored as metadata for convenience)."""
        return {
            "id": self.id,
            "date": self.date,
            "time": self.time,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "mood": self.mood,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entry":
        """Rebuild (and re-validate) an entry from a dictionary, e.g. loaded from disk."""
        try:
            return build_entry(
                data["date"], data["time"], data["category"], data["title"],
                data["content"], data.get("mood"), data.get("id") or None,
            )
        except KeyError as exc:
            raise v.ValidationError(f"Missing field {exc} in entry record.") from None


def build_entry(date_str: str, time_str: str, category: str, title: str,
                content: str, mood=None, entry_id: Optional[str] = None) -> Entry:
    """Validate raw user input and create an :class:`Entry`.

    Raises :class:`journal.validators.ValidationError` on the first invalid field.
    """
    return Entry(
        id=entry_id or uuid.uuid4().hex[:8],
        date=v.validate_date(date_str).isoformat(),
        time=v.validate_time(time_str),
        category=v.validate_category(category),
        title=v.validate_title(title),
        content=v.validate_content(content),
        mood=v.validate_mood(mood),
    )
