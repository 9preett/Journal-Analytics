"""Reproducible demo-data generator (used by the GUI menu, README screenshots and tests)."""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import List

from .models import Entry, build_entry

CATEGORIES = {
    # category: (weight, [title ideas], preferred hours)
    "Personal": (3, ["Quiet evening", "Family call", "Weekend reflections"], (20, 23)),
    "Study": (4, ["DSA practice", "Python project progress", "Exam revision"], (9, 13)),
    "Work": (2, ["Internship notes", "Meeting takeaways", "Task planning"], (14, 18)),
    "Health": (2, ["Morning run", "Gym session", "Sleep log"], (6, 8)),
    "Travel": (1, ["Weekend trip", "New city", "Road journey"], (15, 21)),
    "Gratitude": (2, ["Things I am thankful for", "Small wins"], (21, 23)),
}
FILLER = ("today was productive and I learned something new about myself and my goals "
          "I felt focused and wrote down what mattered most so I can look back later").split()


def generate_entries(n_days: int = 150, seed: int = 42, today: date = None) -> List[Entry]:
    """Create realistic entries over the last ``n_days`` days (never in the future)."""
    rng = random.Random(seed)
    today = today or date.today()
    names = list(CATEGORIES)
    weights = [CATEGORIES[c][0] for c in names]
    entries: List[Entry] = []
    for offset in range(n_days, -1, -1):
        day = today - timedelta(days=offset)
        # more likely to write on weekends, and gradually writing more over time
        chance = 0.45 + 0.25 * (day.weekday() >= 5) + 0.2 * (1 - offset / max(n_days, 1))
        if rng.random() > chance:
            continue
        for _ in range(rng.choice([1, 1, 1, 2])):
            cat = rng.choices(names, weights)[0]
            _, titles, (h_lo, h_hi) = CATEGORIES[cat]
            hour, minute = rng.randint(h_lo, h_hi), rng.randint(0, 59)
            text = " ".join(rng.choices(FILLER, k=rng.randint(15, 90)))
            mood = min(5, max(1, round(rng.gauss(3.6 if cat in ("Health", "Gratitude") else 3.1, 0.9))))
            entries.append(build_entry(day.isoformat(), f"{hour:02d}:{minute:02d}", cat,
                                       rng.choice(titles), text, mood))
    return entries
