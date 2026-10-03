"""Flag runner: ground-truth statement in, stored open flags out (tested on sample data).

Usage: python -m backend.flags.run problem
"""
import json
import os
import sys
from datetime import datetime, timezone

from backend.common import store
from backend.flags import rules

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_flags(statement_id, statement=None):
    """Run all rules on data/ground_truth/<id>.json and save the flags.

    Idempotent: save_flags replaces that statement's flags. Returns the saved flags.
    """
    if statement is None:
        with open(os.path.join(ROOT, "data", "ground_truth", f"{statement_id}.json")) as fh:
            statement = json.load(fh)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prefix = f'{statement_id}-' if statement_id.startswith('upload-') else ''
    flags = [{"id": f"{prefix}f{i}", **flag, "statement_id": statement_id, "created_at": now, "status": "open"}
             for i, flag in enumerate(rules.run_all(statement), 1)]
    return store.save_flags(statement_id, flags)


if __name__ == "__main__":
    for sid in sys.argv[1:] or ["clean", "problem"]:
        saved = run_flags(sid)
        print(f"{sid}: {len(saved)} open flag(s)")
        for f in saved:
            print(f"  {f['id']} {f['rule']}: {f['reason']}")
