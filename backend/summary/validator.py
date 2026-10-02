"""Number validator: every dollar figure in a summary must come from statement.json.

validate(summary_text, statement) -> {"figures_checked": int, "mismatches": [str]}

Figures recognised: $1,031.50  $48,000  $412300.12  $5 (a leading "$", digits with
optional thousands commas and optional cents). Shorthand such as $412K or $1.2 million
is NOT accepted: the figure is reported as a mismatch so the summarizer is told to
write the full number. Comparison is exact to the cent.

A figure is valid if it equals one of:
  * listed values: account start/end values, fee amounts, transaction amounts,
    prior_fee_total;
  * derived values: each account's change (end - start, absolute), total start,
    total end, total change, total fees, fee change versus prior_fee_total, the total
    of each transaction type (e.g. all withdrawals), and the sum of any 2 or 3
    transactions of the same type (covers "3 withdrawals totaling $5,550").
Signs are ignored ("down $5,000" and "$5,000" both compare as 5000.00).
Anything else, including a number that is close to a real one, is a mismatch.
"""
import re
from decimal import Decimal
from itertools import combinations

_FIGURE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)(\s?(?:[KkMmBb]\b|thousand|million|billion))?")


def _cents(x):
    return int((Decimal(str(x)) * 100).to_integral_value())


def allowed_cents(statement):
    """Set of allowed dollar values, in cents."""
    ok = set()
    accounts = statement.get("accounts", [])
    starts = [_cents(a["start_value"]) for a in accounts]
    ends = [_cents(a["end_value"]) for a in accounts]
    ok.update(starts, ends)
    ok.update(abs(e - s) for s, e in zip(starts, ends))
    if accounts:
        ok.update([sum(starts), sum(ends), abs(sum(ends) - sum(starts))])
    fees = [_cents(f["amount"]) for f in statement.get("fees", [])]
    ok.update(fees)
    if fees:
        ok.add(sum(fees))
    if statement.get("prior_fee_total") is not None:
        prior = _cents(statement["prior_fee_total"])
        ok.add(prior)
        if fees:
            ok.add(abs(sum(fees) - prior))
    by_type = {}
    for t in statement.get("transactions", []):
        by_type.setdefault(t["type"], []).append(_cents(t["amount"]))
    ok.add(sum(by_type.get("withdrawal", []) + by_type.get("wire", [])))
    for amounts in by_type.values():
        ok.update(amounts)
        ok.add(sum(amounts))
        for n in (2, 3):
            ok.update(sum(c) for c in combinations(amounts, n))
    return ok


def validate(summary_text, statement):
    ok = allowed_cents(statement)
    mismatches, checked = [], 0
    for m in _FIGURE.finditer(summary_text):
        checked += 1
        text = m.group(0).strip()
        if m.group(2):
            mismatches.append(f"{text} (write the full figure, not shorthand)")
        elif _cents(m.group(1).replace(",", "")) not in ok:
            mismatches.append(text)
    return {"figures_checked": checked, "mismatches": mismatches}
