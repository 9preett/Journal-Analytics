import json
import tempfile
import unittest
from pathlib import Path

from journal.models import Entry, build_entry
from journal.storage import JournalStorage, StorageError, export_csv, import_csv
from journal.validators import ValidationError


def make(day="2024-03-01", cat="study", mood=3, text="one two three"):
    return build_entry(day, "10:30", cat, "Title", text, mood)


class ModelTests(unittest.TestCase):
    def test_word_count_and_normalisation(self):
        e = make(text="  hello brave   new world ")
        self.assertEqual(e.word_count, 4)
        self.assertEqual(e.category, "Study")

    def test_round_trip_dict(self):
        e = make()
        self.assertEqual(Entry.from_dict(e.to_dict()), e)

    def test_from_dict_missing_field(self):
        with self.assertRaises(ValidationError):
            Entry.from_dict({"date": "2024-03-01"})

    def test_build_entry_rejects_bad_input(self):
        with self.assertRaises(ValidationError):
            build_entry("2024-03-01", "10:30", "Study", "T", "text", mood=9)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_gives_empty_list(self):
        self.assertEqual(JournalStorage(self.dir / "none.json").load(), [])

    def test_save_and_load(self):
        store = JournalStorage(self.dir / "sub" / "j.json")
        entries = [make("2024-03-01"), make("2024-03-02", cat="work", mood=None)]
        store.save(entries)
        self.assertEqual(store.load(), entries)

    def test_corrupt_file_is_backed_up(self):
        path = self.dir / "j.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(StorageError):
            JournalStorage(path).load()
        self.assertTrue((self.dir / "j.corrupt.bak").exists())

    def test_invalid_records_are_skipped(self):
        path = self.dir / "j.json"
        good = make().to_dict()
        path.write_text(json.dumps({"entries": [good, {"date": "bad"}, "junk"]}), encoding="utf-8")
        store = JournalStorage(path)
        self.assertEqual(len(store.load()), 1)
        self.assertEqual(store.skipped, 2)

    def test_csv_round_trip(self):
        entries = [make("2024-03-01"), make("2024-03-05", cat="health", mood=None)]
        path = self.dir / "out.csv"
        export_csv(entries, path)
        loaded, skipped = import_csv(path)
        self.assertEqual(loaded, entries)
        self.assertEqual(skipped, 0)

    def test_import_missing_file(self):
        with self.assertRaises(StorageError):
            import_csv(self.dir / "nope.csv")


if __name__ == "__main__":
    unittest.main()
