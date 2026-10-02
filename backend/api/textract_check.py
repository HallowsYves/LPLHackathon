"""Side check: how much of a statement PDF does Textract read correctly? (sample data)

diff_against_ground_truth(statement_id) -> {"statement_id", "found": [...], "missing": [...],
"match_rate": 0..1} or {"statement_id", "error": "..."}. Never raises, and nothing in the
demo path depends on it: the flags and summary always use the ground-truth JSON.

Sends data/pdfs/<id>.pdf (single page) to AnalyzeDocument with TABLES + FORMS, collects the
text, and looks for each ground-truth dollar amount (compared to the cent) and each
transaction date (accepts 2026-09-12, 09/12/2026, 9/12/2026 and Sep 12, 2026).
Env: AWS_REGION. Usage: python -m backend.api.textract_check [problem clean]
"""
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AMOUNT = re.compile(r"\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d{1,2})?")


def _amount_cents(text):
    return {int(round(float(m.group(1).replace(",", "") + (m.group(2) or "")) * 100))
            for m in _AMOUNT.finditer(text)}


def _date_forms(iso):
    d = date.fromisoformat(iso)
    return {iso, f"{d.month:02d}/{d.day:02d}/{d.year}", f"{d.month}/{d.day}/{d.year}",
            f"{d.strftime('%b')} {d.day}, {d.year}", f"{d.strftime('%b')} {d.day:02d}, {d.year}"}


def _expected(statement):
    items = []
    for a in statement["accounts"]:
        items += [("amount", f"{a['id']} start_value", a["start_value"]),
                  ("amount", f"{a['id']} end_value", a["end_value"])]
    items += [("amount", f"fee: {f['label']}", f["amount"]) for f in statement["fees"]]
    for t in statement["transactions"]:
        items += [("amount", f"{t['id']} amount", t["amount"]), ("date", f"{t['id']} date", t["date"])]
    if statement.get("prior_fee_total") is not None:
        items.append(("amount", "prior_fee_total", statement["prior_fee_total"]))
    return items


def _read_text(pdf_bytes, client=None):
    if client is None:
        import boto3
        client = boto3.client("textract", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    resp = client.analyze_document(Document={"Bytes": pdf_bytes}, FeatureTypes=["TABLES", "FORMS"])
    return "\n".join(b["Text"] for b in resp["Blocks"] if b["BlockType"] == "LINE" and "Text" in b)


def diff_against_ground_truth(statement_id, client=None):
    try:
        with open(os.path.join(ROOT, "data", "ground_truth", f"{statement_id}.json")) as fh:
            statement = json.load(fh)
        with open(os.path.join(ROOT, "data", "pdfs", f"{statement_id}.pdf"), "rb") as fh:
            text = _read_text(fh.read(), client)
        cents = _amount_cents(text)
        found, missing = [], []
        for kind, label, value in _expected(statement):
            if kind == "amount":
                hit = int(round(value * 100)) in cents
            else:
                hit = any(f in text for f in _date_forms(value))
            (found if hit else missing).append(f"{label}: {value}")
        total = len(found) + len(missing)
        return {"statement_id": statement_id, "found": found, "missing": missing,
                "match_rate": round(len(found) / total, 3) if total else 0.0}
    except Exception as e:
        return {"statement_id": statement_id, "error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    for sid in sys.argv[1:] or ["clean", "problem"]:
        r = diff_against_ground_truth(sid)
        print(json.dumps({k: v for k, v in r.items() if k != "found"}, indent=2))
        print(f"{sid}: match_rate={r.get('match_rate')} (tested on sample data)")
