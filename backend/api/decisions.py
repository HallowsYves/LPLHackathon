"""Advisor decisions and audit trail (tested on sample data).

decide(flag_id, action, note) -> audit record. A human decides everything: this
only records the choice, it never places a hold or contacts anyone.
get_audit(statement_id) -> audit records, oldest first.

Errors: DecisionError (bad action, missing note for escalate; HTTP 400),
KeyError (unknown flag; 404), ConflictError (flag already decided; 409).
"""
from datetime import datetime, timezone

from backend.common import store

ADVISOR = "Dana Ortiz (demo advisor)"
STATUS = {"approve": "approved", "escalate": "escalated", "dismiss": "dismissed"}


class DecisionError(ValueError):
    pass


class ConflictError(Exception):
    pass


def decide(flag_id, action, note=""):
    if action not in STATUS:
        raise DecisionError("action must be approve, escalate or dismiss")
    note = (note or "").strip()
    if action == "escalate" and not note:
        raise DecisionError("a note is required to escalate")
    flag = store.get_flag(flag_id)
    if flag is None:
        raise KeyError(flag_id)
    if flag["status"] != "open":
        raise ConflictError(f"flag {flag_id} was already {flag['status']}")
    store.update_flag_status(flag_id, STATUS[action])
    return store.add_audit({
        "statement_id": flag["statement_id"], "flag_id": flag_id, "advisor": ADVISOR,
        "action": action, "note": note,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def get_audit(statement_id):
    return store.list_audit(statement_id)
