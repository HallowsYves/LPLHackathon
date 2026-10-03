"""Plain-language summary of a statement (tested on sample data).

summarize(statement) -> {"statement_id"?, "text", "validation": {...}}
(statement_id is added by summarize_id; audio_url is added later by the API layer.)

Bedrock only writes wording. Every dollar figure is checked by validator.validate
against the statement; on a mismatch (or a banned word) we regenerate up to
MAX_ATTEMPTS times, telling the model what was wrong. If every attempt fails we
return a deterministic template filled straight from the JSON (used_fallback true).

Pass lang="es" to get a machine-translated Spanish summary via translate_summary.
The English summary is always generated and validated first; translation happens after.
If figures do not survive translation, the English text is returned with
machine_translated=False. "en" (default) skips translation entirely.

Env: AWS_REGION, BEDROCK_MODEL_ID; optional GUARDRAIL_ID and GUARDRAIL_VERSION
(version defaults to DRAFT) are applied to the model's output when set. They are
not applied to the input: the statement JSON itself (IRA, brokerage, wires) trips the
investment-advice topic, and the point is to police what the model writes.

Usage: python -m backend.summary.summarize problem [--mock] [--lang=es]
"""
import json
import os
import sys

from backend.summary.validator import validate

MAX_ATTEMPTS = 3
BANNED = ("fraud", "scam", "stolen", "steal")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SYSTEM_PROMPT = """You write short plain-language summaries of brokerage statements for clients aged 75 and older.
You receive the statement as JSON. Rules:
- Use short sentences and everyday words. No jargon.
- Cover, in this order: (1) total account value now and how each account changed, (2) what moved in or out (deposits, withdrawals, wires, dividends), (3) fees paid this period, (4) then a heading "Questions to ask your advisor" with 2 or 3 short questions.
- Every dollar amount must be copied exactly from the JSON or be a sum or difference of listed amounts. Write full figures like $1,031.50 or $48,000. Never use K, M, "thousand" or "million". Do not round. Do not invent any number.
- Do not give investment advice (no buy, sell or hold suggestions). Do not use the words fraud, scam or theft, and do not suggest anyone did anything wrong. If something is unusual, say it may be worth a call to the advisor.
- Plain text only, no markdown symbols, no tables. Keep it under 250 words."""


def _money(x):
    return f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"


def template_summary(statement):
    """Deterministic summary built only from statement values."""
    accts = statement["accounts"]
    start = sum(a["start_value"] for a in accts)
    end = sum(a["end_value"] for a in accts)
    fees = sum(f["amount"] for f in statement["fees"])
    prior = statement.get("prior_fee_total")
    first = statement["client"]["name"].split()[0]
    lines = [f"Here is your statement summary for {statement['period']}, {first}.", "",
             f"Your accounts together are worth {_money(end)}. At the start of the period they were worth {_money(start)}."]
    for a in accts:
        change = a["end_value"] - a["start_value"]
        word = "up" if change >= 0 else "down"
        lines.append(f"Your {a['type']} ended at {_money(a['end_value'])}, {word} {_money(abs(change))}.")
    outflow = [t for t in statement["transactions"] if t["type"] in ("withdrawal", "wire")]
    if outflow:
        lines += ["", f"Money sent out this period: {len(outflow)} payments totaling "
                      f"{_money(sum(t['amount'] for t in outflow))}."]
        big = max(outflow, key=lambda t: t["amount"])
        lines.append(f"The largest was {_money(big['amount'])} on {big['date']}"
                     + (f" to {big['payee']}." if big.get("payee") else "."))
    lines += ["", f"Fees paid this period: {_money(fees)}."
              + (f" Last period they were {_money(prior)}." if prior is not None else "")]
    lines += ["", "Questions to ask your advisor:"]
    if outflow:
        lines.append(f"1. Can you explain the {_money(big['amount'])} payment on {big['date']}?")
    else:
        lines.append("1. Is there anything on this statement I should know about?")
    lines.append("2. What does each fee on this statement cover?")
    lines.append("3. Is there anything on this statement you would like to go over with me?")
    return "\n".join(lines)


def _client():
    import boto3
    return boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION"))


def _generate(client, statement, problems):
    prompt = "Statement JSON:\n" + json.dumps(statement, indent=2)
    if problems:
        prompt += ("\n\nYour previous draft had problems: " + "; ".join(problems)
                   + ". Rewrite the summary and fix them. Use only amounts from the JSON.")
    kwargs = {
        "modelId": os.environ["BEDROCK_MODEL_ID"],
        "system": [{"text": SYSTEM_PROMPT}],
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": 700, "temperature": 0.2},
    }
    resp = client.converse(**kwargs)
    text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"]).strip()
    if os.environ.get("GUARDRAIL_ID") and _guardrail_blocks(text):
        return None
    return text


def _guardrail_blocks(text):
    import boto3
    rt = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION"))
    r = rt.apply_guardrail(guardrailIdentifier=os.environ["GUARDRAIL_ID"],
                           guardrailVersion=os.environ.get("GUARDRAIL_VERSION", "DRAFT"),
                           source="OUTPUT", content=[{"text": {"text": text}}])
    return r["action"] == "GUARDRAIL_INTERVENED"


def summarize(statement, mock=False, client=None, lang="en"):
    """Return {"text", "validation", "machine_translated": bool}.

    lang="en" (default): English only.
    lang="es": English summary is generated and validated first, then translated
               via Amazon Translate. If figures fail post-translation validation,
               falls back to English with machine_translated=False.
    validation has figures_checked, mismatches, attempts, used_fallback.
    """
    if mock:
        text = template_summary(statement)
        v = validate(text, statement)
        result = {"text": text, "validation": {**v, "attempts": 0, "used_fallback": True},
                  "machine_translated": False}
    else:
        client = client or _client()
        problems = []
        result = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            text = _generate(client, statement, problems)
            if text is None:
                problems = ["the response was blocked by a safety filter; keep to plain facts about the statement"]
                continue
            v = validate(text, statement)
            bad = [w for w in BANNED if w in text.lower()]
            problems = [f"figure {m} is not in the data" for m in v["mismatches"]] \
                + [f"do not use the word '{w}'" for w in bad]
            if not problems:
                result = {"text": text, "validation": {**v, "attempts": attempt, "used_fallback": False},
                          "machine_translated": False}
                break
        if result is None:
            text = template_summary(statement)
            v = validate(text, statement)
            result = {"text": text, "validation": {**v, "attempts": MAX_ATTEMPTS, "used_fallback": True},
                      "machine_translated": False}

    if lang != "en":
        from backend.summary.translate import translate_summary
        if mock:
            # In mock mode skip the AWS Translate call; return the English text
            # with machine_translated=False so the UI shows the fallback notice.
            result["machine_translated"] = False
        else:
            tr = translate_summary(result["text"], lang, statement)
            result["text"] = tr["text"]
            result["machine_translated"] = tr["machine_translated"]

    return result


def summarize_id(statement_id, mock=False, lang="en"):
    with open(os.path.join(ROOT, "data", "ground_truth", f"{statement_id}.json")) as fh:
        statement = json.load(fh)
    return {"statement_id": statement_id, **summarize(statement, mock=mock, lang=lang)}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lang_arg = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--lang=")), "en")
    result = summarize_id(args[0] if args else "problem", mock="--mock" in sys.argv, lang=lang_arg)
    print(result["text"])
    print(f"\nmachine_translated: {result.get('machine_translated', False)}")
    print("\n" + json.dumps(result["validation"]))
