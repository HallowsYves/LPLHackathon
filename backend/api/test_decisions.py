import os
import tempfile
import unittest

from backend.api import decisions
from backend.common import store


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["STORE"] = "local"
        os.environ["LOCAL_STORE_DIR"] = self.tmp.name
        store.save_flags("problem", [
            {"id": f"f{i}", "rule": "fee_jump", "txn_ids": [], "reason": "Worth a call.",
             "status": "open", "created_at": "2026-10-03T00:00:00Z"} for i in (1, 2, 3, 4)])

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("LOCAL_STORE_DIR", None)

    def test_each_action_sets_status_and_audits(self):
        for fid, action, status in (("f1", "approve", "approved"), ("f2", "escalate", "escalated"),
                                    ("f3", "dismiss", "dismissed")):
            rec = decisions.decide(fid, action, "checked with client")
            self.assertEqual(store.get_flag(fid)["status"], status)
            self.assertEqual((rec["flag_id"], rec["action"], rec["advisor"]),
                             (fid, action, "Dana Ortiz (demo advisor)"))
            self.assertTrue(rec["timestamp"].endswith("Z"))
        self.assertEqual(len(decisions.get_audit("problem")), 3)
        self.assertEqual(store.get_flag("f4")["status"], "open")

    def test_note_optional_except_escalate(self):
        decisions.decide("f1", "dismiss")
        for note in ("", "   ", None):
            with self.assertRaises(decisions.DecisionError):
                decisions.decide("f2", "escalate", note)
        self.assertEqual(store.get_flag("f2")["status"], "open")
        self.assertEqual(len(decisions.get_audit("problem")), 1)

    def test_bad_action_and_unknown_flag(self):
        with self.assertRaises(decisions.DecisionError):
            decisions.decide("f1", "hold", "x")
        with self.assertRaises(KeyError):
            decisions.decide("nope", "approve", "x")

    def test_double_decision_refused(self):
        decisions.decide("f1", "escalate", "call client")
        with self.assertRaises(decisions.ConflictError):
            decisions.decide("f1", "dismiss", "changed my mind")
        self.assertEqual(store.get_flag("f1")["status"], "escalated")
        self.assertEqual(len(decisions.get_audit("problem")), 1)


if __name__ == "__main__":
    unittest.main()
