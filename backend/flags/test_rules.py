import json
import os
import unittest

from backend.flags import rules

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def txn(i, date, typ, amount, payee="Someone", new=False):
    return {"id": i, "date": date, "type": typ, "payee": payee, "amount": amount, "payee_is_new": new}


def stmt(txns, fees=640.00, prior=640.00):
    return {"client": {"name": "Test Client", "age": 78}, "period": "2026-Q3", "accounts": [],
            "fees": [{"label": "Advisory fee", "amount": fees}], "transactions": txns,
            "prior_fee_total": prior}


CLEAN = stmt([
    txn("t1", "2026-07-05", "withdrawal", 800, "Known Bank"),
    txn("t2", "2026-08-05", "withdrawal", 800, "Known Bank"),
    txn("t3", "2026-09-05", "withdrawal", 800, "Known Bank"),
    txn("t4", "2026-09-10", "wire", 48000, "Old Payee LLC", new=False),
    txn("t5", "2026-09-11", "wire", 9000, "Fresh Payee LLC", new=True),
], fees=655.00)

PROBLEM = stmt([
    txn("t1", "2026-07-05", "withdrawal", 800, "Known Bank"),
    txn("t7", "2026-09-12", "wire", 48000, "Greenfield Holdings LLC", new=True),
    txn("t8", "2026-09-14", "withdrawal", 2200, "Known Bank"),
    txn("t10", "2026-09-16", "withdrawal", 1900, "Shop A", new=True),
    txn("t11", "2026-09-18", "withdrawal", 1450, "Shop B", new=True),
], fees=1031.50)


class RuleTests(unittest.TestCase):
    def test_clean_has_no_flags(self):
        self.assertEqual(rules.run_all(CLEAN), [])

    def test_problem_has_exactly_three_flags(self):
        flags = rules.run_all(PROBLEM)
        self.assertEqual([f["rule"] for f in flags],
                         ["large_wire_new_payee", "rapid_withdrawals", "fee_jump"])

    def test_wire_flag(self):
        (f,) = rules.large_wire_new_payee(PROBLEM)
        self.assertEqual(f["txn_ids"], ["t7"])
        self.assertIn("$48,000", f["reason"])

    def test_wire_boundary(self):
        at = stmt([txn("t1", "2026-09-01", "wire", rules.LARGE_WIRE_MIN, new=True)])
        below = stmt([txn("t1", "2026-09-01", "wire", rules.LARGE_WIRE_MIN - 1, new=True)])
        self.assertEqual(len(rules.large_wire_new_payee(at)), 1)
        self.assertEqual(rules.large_wire_new_payee(below), [])

    def test_rapid_flag(self):
        (f,) = rules.rapid_withdrawals(PROBLEM)
        self.assertEqual(f["txn_ids"], ["t8", "t10", "t11"])
        self.assertIn("$5,550", f["reason"])

    def test_rapid_needs_total_and_count(self):
        small = stmt([txn(f"t{i}", f"2026-09-0{i}", "withdrawal", 500) for i in (1, 2, 3)])
        two = stmt([txn("t1", "2026-09-01", "withdrawal", 9000), txn("t2", "2026-09-02", "withdrawal", 9000)])
        spread = stmt([txn(f"t{i}", f"2026-09-{d}", "withdrawal", 3000) for i, d in ((1, "01"), (2, "10"), (3, "20"))])
        for s in (small, two, spread):
            self.assertEqual(rules.rapid_withdrawals(s), [])

    def test_rapid_overlapping_windows_one_flag(self):
        dates = ["2026-09-01", "2026-09-04", "2026-09-07", "2026-09-10"]
        s = stmt([txn(f"t{i}", d, "withdrawal", 2000) for i, d in enumerate(dates, 1)])
        (f,) = rules.rapid_withdrawals(s)
        self.assertEqual(f["txn_ids"], ["t1", "t2", "t3", "t4"])

    def test_fee_flag(self):
        (f,) = rules.fee_jump(PROBLEM)
        self.assertEqual(f["txn_ids"], [])
        self.assertIn("61%", f["reason"])

    def test_fee_boundary_and_missing_prior(self):
        self.assertEqual(rules.fee_jump(stmt([], fees=800.00)), [])  # exactly +25%
        self.assertEqual(len(rules.fee_jump(stmt([], fees=800.01))), 1)
        self.assertEqual(rules.fee_jump(stmt([], fees=900, prior=0)), [])

    def test_reasons_are_calm(self):
        for f in rules.run_all(PROBLEM):
            self.assertIn("worth a call", f["reason"].lower())
            self.assertNotIn("fraud", f["reason"].lower())
            self.assertEqual(f["status"], "open")


class GroundTruthTests(unittest.TestCase):
    def load(self, name):
        path = os.path.join(ROOT, "data", "ground_truth", f"{name}.json")
        if not os.path.exists(path):
            self.skipTest("ground truth not present")
        with open(path) as fh:
            return json.load(fh)

    def test_ground_truth_clean(self):
        self.assertEqual(rules.run_all(self.load("clean")), [])

    def test_ground_truth_problem(self):
        self.assertEqual([f["rule"] for f in rules.run_all(self.load("problem"))],
                         ["large_wire_new_payee", "rapid_withdrawals", "fee_jump"])


if __name__ == "__main__":
    unittest.main()
