import os
import unittest

os.environ.setdefault("MPLBACKEND", "Agg")

from matplotlib.figure import Figure

from journal import analytics as an
from journal import visuals
from journal.sample_data import generate_entries


class VisualsTests(unittest.TestCase):
    def test_every_chart_draws_with_data_and_when_empty(self):
        full = an.entries_to_dataframe(generate_entries(90, seed=3))
        empty = an.entries_to_dataframe([])
        for name, builder in visuals.CHARTS.items():
            for label, df in (("data", full), ("empty", empty)):
                with self.subTest(chart=name, case=label):
                    fig = builder(df)
                    self.assertIsInstance(fig, Figure)
                    self.assertGreaterEqual(len(fig.axes), 1)

    def test_reuses_supplied_figure(self):
        fig = Figure()
        df = an.entries_to_dataframe(generate_entries(30, seed=5))
        self.assertIs(visuals.category_bar(df, fig), fig)
        self.assertIs(visuals.weekday_heatmap(df, fig), fig)


if __name__ == "__main__":
    unittest.main()
