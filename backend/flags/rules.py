"""Flag rules: plain Python, explainable, no AI (tested on sample data).

Each rule takes a statement.json dict and returns a list of flag dicts
(rule, txn_ids, reason, status). The caller assigns ids and adds statement_id
and created_at. A flag is "worth a call", never a verdict.
"""
from datetime import date

LARGE_WIRE_MIN = 10000
RAPID_COUNT = 3
RAPID_DAYS = 7
RAPID_TOTAL_MIN = 5000
FEE_JUMP_PCT = 25


def _money(x):
    return f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"


def _flag(rule, txn_ids, reason):
    return {"rule": rule, "txn_ids": txn_ids, "reason": reason, "status": "open"}


def large_wire_new_payee(statement):
    """One flag per wire of at least LARGE_WIRE_MIN to a payee not seen before."""
    flags = []
    for t in statement["transactions"]:
        if t["type"] == "wire" and t["amount"] >= LARGE_WIRE_MIN and t.get("payee_is_new"):
            flags.append(_flag(
                "large_wire_new_payee", [t["id"]],
                f"A {_money(t['amount'])} wire on {t['date']} went to {t.get('payee', 'a payee')}, "
                f"a payee not seen before. Worth a call."))
    return flags


def rapid_withdrawals(statement):
    """RAPID_COUNT or more withdrawals within RAPID_DAYS days (first to last date,
    inclusive of RAPID_DAYS) totaling at least RAPID_TOTAL_MIN. Wires are not
    counted here; overlapping windows are merged into one flag."""
    wds = sorted((t for t in statement["transactions"] if t["type"] == "withdrawal"),
                 key=lambda t: (t["date"], t["id"]))
    day = lambda t: date.fromisoformat(t["date"])
    clusters = []
    for i, first in enumerate(wds):
        window = [t for t in wds[i:] if (day(t) - day(first)).days <= RAPID_DAYS]
        if len(window) >= RAPID_COUNT and sum(t["amount"] for t in window) >= RAPID_TOTAL_MIN:
            ids = {t["id"] for t in window}
            for c in [c for c in clusters if c & ids]:
                clusters.remove(c)
                ids |= c
            clusters.append(ids)
    by_id = {t["id"]: t for t in wds}
    flags = []
    for ids in sorted(clusters, key=lambda c: min(by_id[i]["date"] for i in c)):
        group = sorted((by_id[i] for i in ids), key=lambda t: (t["date"], t["id"]))
        span = (day(group[-1]) - day(group[0])).days
        flags.append(_flag(
            "rapid_withdrawals", [t["id"] for t in group],
            f"{len(group)} withdrawals totaling {_money(sum(t['amount'] for t in group))} were made "
            f"between {group[0]['date']} and {group[-1]['date']} ({span} days apart). Worth a call."))
    return flags


def fee_jump(statement):
    """Flag when total fees exceed prior_fee_total by more than FEE_JUMP_PCT percent."""
    prior = statement.get("prior_fee_total") or 0
    total = sum(f["amount"] for f in statement["fees"])
    if prior <= 0:
        return []
    pct = (total - prior) / prior * 100
    if pct <= FEE_JUMP_PCT:
        return []
    return [_flag(
        "fee_jump", [],
        f"Fees this period were ${total:,.2f}, up {pct:.0f}% from ${prior:,.2f} last period. "
        f"Worth a call.")]


ALL_RULES = (large_wire_new_payee, rapid_withdrawals, fee_jump)


def run_all(statement):
    """Run every rule; returns flags without ids."""
    return [f for rule in ALL_RULES for f in rule(statement)]
