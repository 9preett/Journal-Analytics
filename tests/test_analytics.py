import unittest
from datetime import date

import numpy as np

from journal import analytics as an
from journal.models import build_entry
from journal.sample_data import generate_entries


def e(day, cat="Study", time="10:00", mood=3, text="a b c d e"):
    return build_entry(day, time, cat, "T", text, mood)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        # 2024-03-04 is a Monday
        self.entries = [
            e("2024-03-04", "Study", "09:00", 4), e("2024-03-05", "Study", "21:00", 2),
            e("2024-03-06", "Work", "14:00", 3), e("2024-03-10", "Health", "07:00", 5),
            e("2024-03-10", "Study", "22:00", None),
        ]
        self.df = an.entries_to_dataframe(self.entries)

    def test_dataframe_columns_and_order(self):
        self.assertEqual(len(self.df), 5)
        self.assertTrue(self.df["date"].is_monotonic_increasing)
        self.assertEqual(int(self.df.loc[0, "weekday"]), 0)
        self.assertEqual(int(self.df.loc[0, "hour"]), 9)

    def test_empty_dataframe_is_safe(self):
        empty = an.entries_to_dataframe([])
        self.assertEqual(an.frequency_stats(empty)["total"], 0)
        self.assertEqual(an.longest_streak(empty), 0)
        self.assertEqual(an.current_streak(empty), 0)
        self.assertEqual(an.longest_gap(empty), 0)
        self.assertTrue(an.entries_per_period(empty).empty)
        self.assertEqual(len(an.compare_categories(empty)), 0)
        self.assertEqual(len(an.detect_patterns(empty)), 1)

    def test_counts_by_category(self):
        counts = an.counts_by_category(self.df)
        self.assertEqual(counts["Study"], 3)
        self.assertEqual(counts["Work"], 1)

    def test_entries_per_period_fills_gaps(self):
        daily = an.entries_per_period(self.df, "D")
        self.assertEqual(len(daily), 7)            # 4th..10th
        self.assertEqual(int(daily.sum()), 5)
        self.assertEqual(int(daily.iloc[3]), 0)    # 7th: nothing written
        with self.assertRaises(ValueError):
            an.entries_per_period(self.df, "Y")

    def test_streaks_and_gap(self):
        self.assertEqual(an.longest_streak(self.df), 3)
        self.assertEqual(an.longest_gap(self.df), 3)
        self.assertEqual(an.current_streak(self.df, today=date(2024, 3, 11)), 1)
        self.assertEqual(an.current_streak(self.df, today=date(2024, 3, 20)), 0)

    def test_frequency_stats(self):
        s = an.frequency_stats(self.df)
        self.assertEqual((s["total"], s["span_days"], s["active_days"]), (5, 7, 4))
        self.assertAlmostEqual(s["avg_per_week"], 5.0)

    def test_weekday_distribution_and_matrix(self):
        wd = an.weekday_distribution(self.df)
        self.assertEqual(wd["Sun"], 2)
        self.assertEqual(wd["Mon"], 1)
        matrix = an.weekday_timeslot_matrix(self.df)
        self.assertEqual(matrix.shape, (7, 4))
        self.assertEqual(int(matrix.sum()), 5)
        self.assertEqual(int(matrix[6, 3]), 1)     # Sunday evening
        self.assertEqual(int(matrix[6, 0 + 0]), 0)

    def test_filter_entries(self):
        self.assertEqual(len(an.filter_entries(self.df, category="study")), 3)
        self.assertEqual(len(an.filter_entries(self.df, category="All")), 5)
        self.assertEqual(len(an.filter_entries(self.df, start=date(2024, 3, 6))), 3)
        self.assertEqual(len(an.filter_entries(self.df, end=date(2024, 3, 5))), 2)
        self.assertEqual(len(an.filter_entries(self.df, keyword="HEALTH")), 1)
        self.assertEqual(len(an.filter_entries(self.df, keyword="zzz")), 0)

    def test_compare_categories(self):
        table = an.compare_categories(self.df)
        self.assertEqual(table.index[0], "Study")
        self.assertAlmostEqual(table.loc["Study", "share_pct"], 60.0)
        self.assertAlmostEqual(table.loc["Study", "avg_mood"], 3.0)  # NaN mood ignored

    def test_compare_periods(self):
        table = an.compare_periods(self.df, date(2024, 3, 4), date(2024, 3, 6),
                                   date(2024, 3, 7), date(2024, 3, 10))
        self.assertEqual(table.loc["entries", "period_A"], 3)
        self.assertEqual(table.loc["entries", "period_B"], 2)
        self.assertEqual(table.loc["entries", "change"], -1)
        self.assertEqual(table.loc["top_category", "period_A"], "Study")

    def test_trend_slope_detects_growth(self):
        entries = [e(d.isoformat(), time=f"{8 + k:02d}:00")
                   for week in range(5)
                   for d in [date.fromordinal(date(2024, 3, 4).toordinal() + week * 7)]
                   for k in range(week + 1)]
        slope = an.weekly_trend_slope(an.entries_to_dataframe(entries))
        self.assertAlmostEqual(slope, 1.0)
        self.assertIsNone(an.weekly_trend_slope(self.df.head(1)))

    def test_patterns_and_summary_on_demo_data(self):
        df = an.entries_to_dataframe(generate_entries(n_days=120, seed=1))
        notes = an.detect_patterns(df)
        self.assertGreaterEqual(len(notes), 5)
        self.assertIn("OVERVIEW", an.summary_text(df))
        self.assertTrue(np.isfinite(an.frequency_stats(df)["avg_per_week"]))

    def test_demo_data_is_reproducible_and_not_in_future(self):
        a = generate_entries(60, seed=7, today=date(2024, 6, 1))
        b = generate_entries(60, seed=7, today=date(2024, 6, 1))
        strip_id = lambda items: [{k: v for k, v in x.to_dict().items() if k != "id"} for x in items]
        self.assertEqual(strip_id(a), strip_id(b))   # ids are random on purpose (unique GUI row ids)
        self.assertEqual(len({x.id for x in a}), len(a))
        self.assertTrue(all(x.date <= "2024-06-01" for x in a))


if __name__ == "__main__":
    unittest.main()
