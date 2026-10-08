"""Analysis layer built on Pandas and NumPy.

All functions take the DataFrame produced by :func:`entries_to_dataframe`, so they are
independent of the GUI and easy to unit-test.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .models import Entry

COLUMNS = ["id", "date", "time", "category", "title", "content", "mood", "word_count",
           "hour", "weekday"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# (label, first hour, last hour)
TIME_SLOTS = [("Night\n00-05", 0, 5), ("Morning\n06-11", 6, 11),
              ("Afternoon\n12-17", 12, 17), ("Evening\n18-23", 18, 23)]


# --------------------------------------------------------------------------- data prep
def entries_to_dataframe(entries: List[Entry]) -> pd.DataFrame:
    """Convert entries to a DataFrame with helper columns (hour, weekday, word_count)."""
    if not entries:
        return pd.DataFrame({c: pd.Series(dtype="object") for c in COLUMNS}).astype(
            {"date": "datetime64[ns]", "mood": "float64", "word_count": "int64",
             "hour": "int64", "weekday": "int64"})
    df = pd.DataFrame([e.to_dict() for e in entries])
    df["date"] = pd.to_datetime(df["date"])
    df["mood"] = pd.to_numeric(df["mood"], errors="coerce")
    df["hour"] = df["time"].str[:2].astype(int)
    df["weekday"] = df["date"].dt.weekday
    return df.sort_values(["date", "time"]).reset_index(drop=True)


def filter_entries(df: pd.DataFrame, keyword: str = "", category: str = "",
                   start: Optional[date] = None, end: Optional[date] = None) -> pd.DataFrame:
    """Search/filter: keyword (title/content/category), exact category, inclusive date range."""
    out = df
    keyword = (keyword or "").strip().lower()
    if keyword:
        haystack = (out["title"] + " " + out["content"] + " " + out["category"]).str.lower()
        out = out[haystack.str.contains(keyword, regex=False)]
    if category and category.lower() != "all":
        out = out[out["category"].str.lower() == category.lower()]
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out["date"] <= pd.Timestamp(end)]
    return out


# --------------------------------------------------------------------------- counts & frequency
def counts_by_category(df: pd.DataFrame) -> pd.Series:
    """Number of entries per category, largest first."""
    return df["category"].value_counts()


def entries_per_period(df: pd.DataFrame, freq: str = "W") -> pd.Series:
    """Entry counts per day ('D'), week ('W') or month ('M'), gaps filled with 0."""
    if freq not in ("D", "W", "M"):
        raise ValueError("freq must be 'D', 'W' or 'M'")
    if df.empty:
        return pd.Series(dtype="int64")
    periods = df["date"].dt.to_period(freq)
    counts = periods.value_counts().sort_index()
    full = pd.period_range(periods.min(), periods.max(), freq=freq)
    return counts.reindex(full, fill_value=0)


def frequency_stats(df: pd.DataFrame) -> Dict[str, float]:
    """Overall writing frequency numbers."""
    if df.empty:
        return {"total": 0, "span_days": 0, "active_days": 0, "active_ratio": 0.0,
                "avg_per_week": 0.0, "avg_words": 0.0, "total_words": 0}
    span = (df["date"].max() - df["date"].min()).days + 1
    active = int(df["date"].nunique())
    return {
        "total": int(len(df)),
        "span_days": int(span),
        "active_days": active,
        "active_ratio": active / span,
        "avg_per_week": len(df) / (span / 7) if span >= 7 else float(len(df)),
        "avg_words": float(df["word_count"].mean()),
        "total_words": int(df["word_count"].sum()),
    }


def _day_runs(df: pd.DataFrame) -> np.ndarray:
    """Lengths of runs of consecutive writing days (chronological)."""
    days = np.unique(df["date"].values.astype("datetime64[D]")).astype(np.int64)
    if days.size == 0:
        return np.array([], dtype=int)
    breaks = np.where(np.diff(days) != 1)[0]
    bounds = np.concatenate(([-1], breaks, [days.size - 1]))
    return np.diff(bounds)


def longest_streak(df: pd.DataFrame) -> int:
    """Longest run of consecutive days with at least one entry."""
    runs = _day_runs(df)
    return int(runs.max()) if runs.size else 0


def current_streak(df: pd.DataFrame, today: Optional[date] = None) -> int:
    """Streak ending today or yesterday (0 if the last entry is older)."""
    if df.empty:
        return 0
    today = today or date.today()
    last = df["date"].max().date()
    if last < today - timedelta(days=1):
        return 0
    return int(_day_runs(df)[-1])


def longest_gap(df: pd.DataFrame) -> int:
    """Longest number of days without writing between two entries."""
    days = np.unique(df["date"].values.astype("datetime64[D]")).astype(np.int64)
    if days.size < 2:
        return 0
    return int(max(np.diff(days).max() - 1, 0))


# --------------------------------------------------------------------------- distributions
def weekday_distribution(df: pd.DataFrame) -> pd.Series:
    counts = df["weekday"].value_counts().reindex(range(7), fill_value=0).sort_index()
    counts.index = WEEKDAYS
    return counts


def weekday_timeslot_matrix(df: pd.DataFrame) -> np.ndarray:
    """7 x 4 matrix of entry counts: weekday (rows) by time-of-day slot (columns)."""
    matrix = np.zeros((7, len(TIME_SLOTS)), dtype=int)
    for col, (_, lo, hi) in enumerate(TIME_SLOTS):
        mask = ((df["hour"] >= lo) & (df["hour"] <= hi)).to_numpy()
        np.add.at(matrix[:, col], df["weekday"].to_numpy()[mask], 1)
    return matrix


# --------------------------------------------------------------------------- comparisons
def compare_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Per-category entries, share %, average words and average mood."""
    if df.empty:
        return pd.DataFrame(columns=["entries", "share_pct", "avg_words", "avg_mood"])
    grouped = df.groupby("category").agg(
        entries=("id", "count"), avg_words=("word_count", "mean"), avg_mood=("mood", "mean"))
    grouped["share_pct"] = grouped["entries"] / grouped["entries"].sum() * 100
    return grouped[["entries", "share_pct", "avg_words", "avg_mood"]] \
        .sort_values("entries", ascending=False).round(2)


def period_summary(df: pd.DataFrame, start: date, end: date) -> Dict[str, object]:
    """Metrics for entries between ``start`` and ``end`` (inclusive)."""
    part = filter_entries(df, start=start, end=end)
    days = (end - start).days + 1
    return {
        "entries": int(len(part)),
        "active_days": int(part["date"].nunique()) if len(part) else 0,
        "entries_per_week": round(len(part) / (days / 7), 2) if days > 0 else 0.0,
        "total_words": int(part["word_count"].sum()) if len(part) else 0,
        "avg_words": round(float(part["word_count"].mean()), 1) if len(part) else 0.0,
        "avg_mood": round(float(part["mood"].mean()), 2) if part["mood"].notna().any() else None,
        "top_category": part["category"].value_counts().idxmax() if len(part) else "-",
    }


def compare_periods(df: pd.DataFrame, a_start: date, a_end: date,
                    b_start: date, b_end: date) -> pd.DataFrame:
    """Side-by-side comparison of two date ranges with absolute change (B - A)."""
    a, b = period_summary(df, a_start, a_end), period_summary(df, b_start, b_end)
    rows = []
    for key in a:
        change = None
        if isinstance(a[key], (int, float)) and isinstance(b[key], (int, float)):
            change = round(b[key] - a[key], 2)
        rows.append({"metric": key, "period_A": a[key], "period_B": b[key], "change": change})
    return pd.DataFrame(rows).set_index("metric")


# --------------------------------------------------------------------------- patterns
def weekly_trend_slope(df: pd.DataFrame) -> Optional[float]:
    """Slope (entries/week per week) of a least-squares line through weekly counts."""
    weekly = entries_per_period(df, "W")
    if len(weekly) < 3:
        return None
    x = np.arange(len(weekly))
    return float(np.polyfit(x, weekly.to_numpy(dtype=float), 1)[0])


def detect_patterns(df: pd.DataFrame, today: Optional[date] = None) -> List[str]:
    """Plain-English insights about writing habits."""
    if df.empty:
        return ["No entries yet - add some entries to see insights."]
    notes: List[str] = []

    wd = weekday_distribution(df)
    full_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    best, worst = int(wd.to_numpy().argmax()), int(wd.to_numpy().argmin())
    notes.append(f"You write most on {full_names[best]}s ({wd.iloc[best]} entries) "
                 f"and least on {full_names[worst]}s ({wd.iloc[worst]}).")

    slot_totals = weekday_timeslot_matrix(df).sum(axis=0)
    slot = TIME_SLOTS[int(slot_totals.argmax())][0].split("\n")[0].lower()
    pct = slot_totals.max() / slot_totals.sum() * 100
    notes.append(f"Your favourite time to write is the {slot} ({pct:.0f}% of entries).")

    cats = counts_by_category(df)
    notes.append(f"'{cats.index[0]}' is your top category "
                 f"({cats.iloc[0] / len(df) * 100:.0f}% of all entries).")

    weekend = df["weekday"].isin([5, 6]).mean() * 100
    notes.append(f"{weekend:.0f}% of entries are written on weekends "
                 f"({'more' if weekend > 2 / 7 * 100 else 'fewer'} than an even spread of 29%).")

    notes.append(f"Longest streak: {longest_streak(df)} day(s); current streak: "
                 f"{current_streak(df, today)} day(s); longest break: {longest_gap(df)} day(s).")

    slope = weekly_trend_slope(df)
    if slope is not None:
        if slope > 0.05:
            notes.append(f"Trend: writing frequency is increasing (+{slope:.2f} entries/week each week).")
        elif slope < -0.05:
            notes.append(f"Trend: writing frequency is decreasing ({slope:.2f} entries/week each week).")
        else:
            notes.append("Trend: your weekly writing frequency is stable.")

    if df["mood"].notna().sum() >= 5:
        mood_by_cat = df.groupby("category")["mood"].mean().dropna()
        notes.append(f"Highest average mood is in '{mood_by_cat.idxmax()}' "
                     f"({mood_by_cat.max():.1f}/5); lowest in '{mood_by_cat.idxmin()}' "
                     f"({mood_by_cat.min():.1f}/5).")
        corr = df[["word_count", "mood"]].dropna().corr().iloc[0, 1]
        if pd.notna(corr) and abs(corr) >= 0.3:
            notes.append(f"Longer entries tend to go with {'better' if corr > 0 else 'lower'} "
                         f"moods (correlation {corr:+.2f}).")
    return notes


def summary_text(df: pd.DataFrame, today: Optional[date] = None) -> str:
    """Formatted multi-line report used by the GUI's Analytics tab."""
    if df.empty:
        return "No entries yet. Add entries or load demo data from the File menu."
    s = frequency_stats(df)
    lines = [
        "OVERVIEW",
        f"  Total entries        : {s['total']}",
        f"  Date range           : {df['date'].min().date()} to {df['date'].max().date()} ({s['span_days']} days)",
        f"  Days with an entry   : {s['active_days']} ({s['active_ratio'] * 100:.0f}% of the range)",
        f"  Average per week     : {s['avg_per_week']:.1f}",
        f"  Total / avg words    : {s['total_words']} / {s['avg_words']:.0f} per entry",
        "",
        "PATTERNS",
    ]
    lines += [f"  * {n}" for n in detect_patterns(df, today)]
    return "\n".join(lines)
