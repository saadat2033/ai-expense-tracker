import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai import _parse_expense_offline  # noqa: E402
from tracker import ExpenseTracker, guess_category  # noqa: E402


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "expenses.json")
        self.t = ExpenseTracker(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_and_persist(self):
        e = self.t.add_expense(12, "food", "lunch", "2026-01-05")
        self.assertEqual(e["id"], 1)
        self.assertEqual(e["category"], "Food")
        reloaded = ExpenseTracker(self.path)
        self.assertEqual(len(reloaded.expenses), 1)

    def test_rejects_bad_amount(self):
        with self.assertRaises(ValueError):
            self.t.add_expense(0, "Food", "x")

    def test_update_and_delete(self):
        e = self.t.add_expense(8, "Transport", "bus")
        self.t.update_expense(e["id"], amount="10", description="taxi")
        self.assertEqual(self.t.get_expense(e["id"])["amount"], 10)
        self.assertTrue(self.t.delete_expense(e["id"]))
        self.assertFalse(self.t.delete_expense(999))

    def test_summaries_and_budget(self):
        self.t.add_expense(10, "Food", "a", "2026-01-01")
        self.t.add_expense(30, "Food", "b", "2026-02-01")
        self.t.add_expense(5, "Transport", "c", "2026-02-02")
        self.assertEqual(self.t.summary_by_category("2026-02"),
                         {"Food": 30, "Transport": 5})
        self.assertEqual(self.t.summary_by_month(),
                         {"2026-01": 10, "2026-02": 35})
        self.t.set_budget("Food", 20)
        self.assertEqual(self.t.over_budget("2026-02"), ["Food"])

    def test_export_csv(self):
        self.t.add_expense(1, "Other", "x")
        out = os.path.join(self.tmp.name, "out.csv")
        self.t.export_csv(out)
        with open(out) as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_guess_category(self):
        self.assertEqual(guess_category("Uber to work"), "Transport")
        self.assertEqual(guess_category("random thing"), "Other")

    def test_offline_parse(self):
        p = _parse_expense_offline("spent 12.50 on pizza yesterday", date(2026, 3, 10))
        self.assertEqual(p["amount"], 12.5)
        self.assertEqual(p["category"], "Food")
        self.assertEqual(p["date"], "2026-03-09")
        self.assertIsNone(_parse_expense_offline("no number", date.today()))


if __name__ == "__main__":
    unittest.main()
