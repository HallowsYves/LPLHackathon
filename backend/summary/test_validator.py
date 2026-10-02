import json
import os
import unittest

from backend.summary.validator import validate

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(ROOT, "data", "ground_truth", "problem.json")) as fh:
    STATEMENT = json.load(fh)


class ValidatorTests(unittest.TestCase):
    def test_correct_summary(self):
        text = ("Your IRA ended the quarter at $417,163.54, up from $412,300.12. "
                "Fees were $1,031.50, compared with $640.00 last quarter. "
                "A $48,000 wire went to Greenfield Holdings LLC. "
                "Three withdrawals totaled $5,550. Your accounts together hold $490,517.57.")
        r = validate(text, STATEMENT)
        self.assertEqual(r["mismatches"], [])
        self.assertEqual(r["figures_checked"], 7)

    def test_wrong_figure(self):
        r = validate("Your IRA ended at $417,163.45 and fees were $1,031.50.", STATEMENT)
        self.assertEqual(r["figures_checked"], 2)
        self.assertEqual(r["mismatches"], ["$417,163.45"])

    def test_invented_figure(self):
        r = validate("You also received a $2,500 bonus. Fees were $640.", STATEMENT)
        self.assertEqual(r["mismatches"], ["$2,500"])

    def test_shorthand_rejected(self):
        r = validate("Your IRA is worth $417K.", STATEMENT)
        self.assertEqual(len(r["mismatches"]), 1)

    def test_no_figures(self):
        self.assertEqual(validate("Nothing to see.", STATEMENT), {"figures_checked": 0, "mismatches": []})


if __name__ == "__main__":
    unittest.main()
