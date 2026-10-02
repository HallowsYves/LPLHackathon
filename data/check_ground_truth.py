"""Consistency check for data/ground_truth/*.json (tested on sample data).

Checks per file: required keys, dates inside the stated period, unique
transaction ids, positive fee amounts, and that each account's change from
start_value to end_value matches its listed transactions and fees.

Balance rule (per account, using the optional "account" key on transactions
and fees):
    end = start + deposits + dividends - withdrawals - wires - fees
          + MARKET_RATE * start
MARKET_RATE is the assumption the synthetic data was generated with (task C):
a flat 0.8% quarterly market change on start_value, rounded to cents.
TOLERANCE is $0.02, i.e. rounding only, so editing any single amount fails.
If transactions carry no "account" key, the check falls back to totals across
all accounts.
"""
import glob
import json
import os
import re
import sys

MARKET_RATE = 0.008
TOLERANCE = 0.02
INFLOWS = {"deposit", "dividend"}
OUTFLOWS = {"withdrawal", "wire"}
TOP_KEYS = ("client", "period", "accounts", "fees", "transactions", "prior_fee_total")
ACCOUNT_KEYS = ("id", "type", "start_value", "end_value")
TXN_KEYS = ("id", "date", "type", "amount")
PERIOD_RE = re.compile(r"^(\d{4})-Q([1-4])$")


def period_bounds(period):
    m = PERIOD_RE.match(period)
    if not m:
        return None
    year, q = m.group(1), int(m.group(2))
    start_month, end_month = 3 * q - 2, 3 * q
    end_day = {3: 31, 6: 30, 9: 30, 12: 31}[end_month]
    return f"{year}-{start_month:02d}-01", f"{year}-{end_month:02d}-{end_day}"


def check(s):
    errs = []
    for k in TOP_KEYS:
        if k not in s:
            errs.append(f"missing key: {k}")
    if errs:
        return errs
    for k in ("name", "age"):
        if k not in s["client"]:
            errs.append(f"client missing key: {k}")
    for a in s["accounts"]:
        for k in ACCOUNT_KEYS:
            if k not in a:
                errs.append(f"account {a.get('id', '?')} missing key: {k}")
    for t in s["transactions"]:
        for k in TXN_KEYS:
            if k not in t:
                errs.append(f"transaction {t.get('id', '?')} missing key: {k}")
    if errs:
        return errs

    bounds = period_bounds(s["period"])
    if bounds is None:
        errs.append(f"period {s['period']!r} is not like 2026-Q3")
    ids = [t["id"] for t in s["transactions"]]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        errs.append(f"duplicate transaction id: {i}")
    for t in s["transactions"]:
        if bounds and not bounds[0] <= t["date"] <= bounds[1]:
            errs.append(f"{t['id']}: date {t['date']} outside {s['period']} {bounds}")
        if t["type"] not in INFLOWS | OUTFLOWS:
            errs.append(f"{t['id']}: unknown type {t['type']!r}")
        if t["amount"] <= 0:
            errs.append(f"{t['id']}: amount must be positive, got {t['amount']}")
    for f in s["fees"]:
        if f["amount"] <= 0:
            errs.append(f"fee {f['label']!r}: amount must be positive, got {f['amount']}")

    tagged = all("account" in t for t in s["transactions"]) and all("account" in f for f in s["fees"])
    groups = {a["id"]: [a] for a in s["accounts"]} if tagged else {"ALL": s["accounts"]}
    for gid, accts in groups.items():
        start = sum(a["start_value"] for a in accts)
        end = sum(a["end_value"] for a in accts)
        net = 0.0
        for t in s["transactions"]:
            if tagged and t["account"] != gid:
                continue
            net += t["amount"] if t["type"] in INFLOWS else -t["amount"]
        for f in s["fees"]:
            if tagged and f["account"] != gid:
                continue
            net -= f["amount"]
        expected = start + net + round(start * MARKET_RATE, 2)
        if abs(expected - end) > TOLERANCE:
            errs.append(
                f"account {gid}: end_value {end:,.2f} but transactions, fees and a "
                f"{MARKET_RATE:.1%} market change give {expected:,.2f} "
                f"(off by {end - expected:+,.2f}, tolerance {TOLERANCE})"
            )
    return errs


def main():
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ground_truth")
    paths = sorted(glob.glob(os.path.join(folder, "*.json")))
    if not paths:
        print(f"FAIL: no JSON files in {folder}")
        return 1
    failed = False
    for p in paths:
        name = os.path.basename(p)
        try:
            with open(p) as fh:
                s = json.load(fh)
        except json.JSONDecodeError as e:
            print(f"FAIL {name}: not valid JSON ({e})")
            failed = True
            continue
        errs = check(s)
        if errs:
            failed = True
            print(f"FAIL {name}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"PASS {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
