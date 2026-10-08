import unittest
from datetime import date, timedelta

from journal import validators as v


class ValidatorTests(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(v.validate_date("2024-02-29"), date(2024, 2, 29))

    def test_invalid_dates(self):
        for bad in ["", "   ", "29-02-2024", "2023-02-29", "abc", None]:
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError):
                v.validate_date(bad)

    def test_future_date_rejected_unless_allowed(self):
        future = (date.today() + timedelta(days=3)).isoformat()
        with self.assertRaises(v.ValidationError):
            v.validate_date(future)
        self.assertEqual(v.validate_date(future, allow_future=True).isoformat(), future)

    def test_optional_date(self):
        self.assertIsNone(v.validate_optional_date(""))
        self.assertIsNone(v.validate_optional_date(None))
        self.assertEqual(v.validate_optional_date("2024-01-05"), date(2024, 1, 5))

    def test_time(self):
        self.assertEqual(v.validate_time("7:05"), "07:05")
        for bad in ["", "24:00", "12:60", "noon"]:
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError):
                v.validate_time(bad)

    def test_category(self):
        self.assertEqual(v.validate_category("  self-care "), "Self-Care")
        for bad in ["", "   ", "x" * 31, "bad$char"]:
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError):
                v.validate_category(bad)

    def test_title_and_content(self):
        self.assertEqual(v.validate_title("  Hi "), "Hi")
        with self.assertRaises(v.ValidationError):
            v.validate_title("")
        with self.assertRaises(v.ValidationError):
            v.validate_title("x" * 101)
        with self.assertRaises(v.ValidationError):
            v.validate_content("   ")

    def test_mood(self):
        self.assertIsNone(v.validate_mood(""))
        self.assertIsNone(v.validate_mood(None))
        self.assertEqual(v.validate_mood("4"), 4)
        for bad in ["0", "6", "x", "2.5"]:
            with self.subTest(bad=bad), self.assertRaises(v.ValidationError):
                v.validate_mood(bad)


if __name__ == "__main__":
    unittest.main()
