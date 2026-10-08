"""Persistent storage: JSON file for the journal, CSV for import/export."""
from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Tuple

from .models import Entry
from .validators import ValidationError

log = logging.getLogger(__name__)
CSV_FIELDS = ["id", "date", "time", "category", "title", "content", "mood", "word_count"]


class StorageError(Exception):
    """Raised when the journal file cannot be read or written."""


class JournalStorage:
    """Reads/writes the list of entries to a JSON file (atomic writes)."""

    def __init__(self, path):
        self.path = Path(path)
        self.skipped = 0  # invalid records ignored during the last load()

    def load(self) -> List[Entry]:
        self.skipped = 0
        if not self.path.exists():
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as exc:
            backup = self.path.with_suffix(".corrupt.bak")
            try:
                os.replace(self.path, backup)
            except OSError:
                backup = None
            raise StorageError(
                f"Journal file was corrupted ({exc}). "
                + (f"A copy was saved as {backup.name}." if backup else "")
            ) from exc
        except OSError as exc:
            raise StorageError(f"Cannot read {self.path}: {exc}") from exc

        records = payload.get("entries", []) if isinstance(payload, dict) else payload
        entries: List[Entry] = []
        for record in records:
            try:
                entries.append(Entry.from_dict(record))
            except (ValidationError, AttributeError, TypeError) as exc:
                self.skipped += 1
                log.warning("Skipping invalid record %r: %s", record, exc)
        return entries

    def save(self, entries: List[Entry]) -> None:
        """Write atomically: dump to a temp file then replace the real one."""
        payload = {"version": 1, "entries": [e.to_dict() for e in entries]}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as exc:
            raise StorageError(f"Cannot save journal to {self.path}: {exc}") from exc


def export_csv(entries: List[Entry], path) -> None:
    try:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for entry in entries:
                writer.writerow(entry.to_dict())
    except OSError as exc:
        raise StorageError(f"Cannot export to {path}: {exc}") from exc


def import_csv(path) -> Tuple[List[Entry], int]:
    """Return ``(valid_entries, skipped_count)`` from a CSV file."""
    entries: List[Entry] = []
    skipped = 0
    try:
        with open(path, "r", newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    entries.append(Entry.from_dict(row))
                except (ValidationError, TypeError):
                    skipped += 1
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise StorageError(f"Cannot import {path}: {exc}") from exc
    return entries, skipped
