"""Render every chart from demo data into docs/screenshots (used for the README)."""
from pathlib import Path

from journal import analytics, visuals
from journal.sample_data import generate_entries

out = Path(__file__).parent / "docs" / "screenshots"
out.mkdir(parents=True, exist_ok=True)
df = analytics.entries_to_dataframe(generate_entries())
for name, builder in visuals.CHARTS.items():
    fname = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_") + ".png"
    builder(df).savefig(out / fname, dpi=110)
    print("saved", fname)
