"""Matplotlib chart builders.

Each function draws onto a ``matplotlib.figure.Figure`` (created if not supplied) and returns it.
Using ``Figure`` directly (not ``pyplot``) lets the Tkinter GUI embed the charts and lets the
tests/screenshot script render them headlessly.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from . import analytics as an

PALETTE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d"]


def _prepare(fig: Optional[Figure]) -> Figure:
    if fig is None:
        return Figure(figsize=(8, 5), dpi=100)
    fig.clear()
    return fig


def _placeholder(fig: Figure, message: str) -> Figure:
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color="gray")
    ax.set_axis_off()
    return fig


def category_bar(df: pd.DataFrame, fig: Optional[Figure] = None) -> Figure:
    """Report 1: entries per category with each bar's share labelled."""
    fig = _prepare(fig)
    if df.empty:
        return _placeholder(fig, "No data to chart yet")
    counts = an.counts_by_category(df)
    ax = fig.add_subplot(111)
    bars = ax.bar(counts.index, counts.to_numpy(), color=PALETTE[: len(counts)])
    for bar, value in zip(bars, counts.to_numpy()):
        ax.annotate(f"{value}\n({value / counts.sum() * 100:.0f}%)",
                    (bar.get_x() + bar.get_width() / 2, value),
                    ha="center", va="bottom", fontsize=9)
    ax.set_title("Entries by Category")
    ax.set_ylabel("Number of entries")
    ax.set_ylim(0, counts.max() * 1.2)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def frequency_line(df: pd.DataFrame, fig: Optional[Figure] = None) -> Figure:
    """Report 2: weekly entry counts, a 4-week moving average and a NumPy trend line."""
    fig = _prepare(fig)
    if df.empty:
        return _placeholder(fig, "No data to chart yet")
    weekly = an.entries_per_period(df, "W")
    x = np.arange(len(weekly))
    y = weekly.to_numpy(dtype=float)
    labels = [p.start_time.strftime("%d %b") for p in weekly.index]
    ax = fig.add_subplot(111)
    ax.bar(x, y, color="#93c5fd", label="Entries per week")
    if len(y) >= 4:
        ma = np.convolve(y, np.ones(4) / 4, mode="valid")
        ax.plot(x[3:], ma, color="#1d4ed8", linewidth=2.2, label="4-week average")
    if len(y) >= 3:
        slope, intercept = np.polyfit(x, y, 1)
        ax.plot(x, slope * x + intercept, "--", color="#dc2626", label=f"Trend ({slope:+.2f}/wk)")
    step = max(1, len(x) // 10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(labels[::step], rotation=35, ha="right")
    ax.set_title("Writing Frequency (entries per week)")
    ax.set_ylabel("Entries")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def weekday_heatmap(df: pd.DataFrame, fig: Optional[Figure] = None) -> Figure:
    """Report 3: when do you write? weekday x time-of-day heatmap."""
    fig = _prepare(fig)
    if df.empty:
        return _placeholder(fig, "No data to chart yet")
    matrix = an.weekday_timeslot_matrix(df)
    ax = fig.add_subplot(111)
    image = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(an.TIME_SLOTS)))
    ax.set_xticklabels([s[0] for s in an.TIME_SLOTS])
    ax.set_yticks(range(7))
    ax.set_yticklabels(an.WEEKDAYS)
    threshold = matrix.max() / 2 if matrix.max() else 0
    for r in range(7):
        for c in range(matrix.shape[1]):
            ax.text(c, r, matrix[r, c], ha="center", va="center",
                    color="white" if matrix[r, c] > threshold else "black")
    fig.colorbar(image, ax=ax, label="Entries")
    ax.set_title("Writing Patterns: Weekday vs Time of Day")
    fig.tight_layout()
    return fig


def mood_wordcount_trend(df: pd.DataFrame, fig: Optional[Figure] = None) -> Figure:
    """Report 4: weekly average mood and word count."""
    fig = _prepare(fig)
    if df.empty:
        return _placeholder(fig, "No data to chart yet")
    weekly = df.set_index("date").resample("W").agg({"mood": "mean", "word_count": "mean"})
    ax1 = fig.add_subplot(211)
    ax1.plot(weekly.index, weekly["mood"], marker="o", color="#7c3aed")
    ax1.set_ylim(1, 5)
    ax1.set_ylabel("Avg mood (1-5)")
    ax1.set_title("Weekly Mood and Entry Length")
    ax1.grid(alpha=0.3)
    ax2 = fig.add_subplot(212, sharex=ax1)
    ax2.bar(weekly.index, weekly["word_count"], width=5, color="#0891b2")
    ax2.set_ylabel("Avg words / entry")
    ax2.grid(axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def monthly_stacked(df: pd.DataFrame, fig: Optional[Figure] = None) -> Figure:
    """Report 5: monthly activity broken down by category (compare periods and categories)."""
    fig = _prepare(fig)
    if df.empty:
        return _placeholder(fig, "No data to chart yet")
    table = (df.assign(month=df["date"].dt.to_period("M").astype(str))
               .pivot_table(index="month", columns="category", values="id",
                            aggfunc="count", fill_value=0))
    ax = fig.add_subplot(111)
    bottom = np.zeros(len(table))
    for i, cat in enumerate(table.columns):
        ax.bar(table.index, table[cat], bottom=bottom, label=cat, color=PALETTE[i % len(PALETTE)])
        bottom += table[cat].to_numpy()
    ax.set_title("Monthly Entries by Category")
    ax.set_ylabel("Entries")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


CHARTS: Dict[str, Callable[..., Figure]] = {
    "Entries by Category": category_bar,
    "Writing Frequency (weekly)": frequency_line,
    "Weekday vs Time-of-Day Heatmap": weekday_heatmap,
    "Mood & Entry Length Trend": mood_wordcount_trend,
    "Monthly Entries by Category": monthly_stacked,
}
