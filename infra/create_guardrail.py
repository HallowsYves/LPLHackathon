"""Create (idempotently, by name) the Clear Statement Bedrock Guardrail.

Denies two topics: fraud accusations and investment advice (buy/sell/hold).
Prints the guardrail id and version. Tested on sample data.

Usage:
  python infra/create_guardrail.py            # create or reuse, print id + version
  python infra/create_guardrail.py --test     # also check an advice prompt is blocked

Then export what it prints so backend/summary/summarize.py applies it:
  export GUARDRAIL_ID=<id>
  export GUARDRAIL_VERSION=<version>     # defaults to DRAFT if unset
Env: AWS_REGION.
"""
import os
import sys

import boto3

NAME = "clear-statement-guardrail"
BLOCKED = "Sorry, I can only explain what is on the statement in plain words."


def _client():
    return boto3.client("bedrock", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def find(client):
    for page in client.get_paginator("list_guardrails").paginate():
        for g in page["guardrails"]:
            if g["name"] == NAME:
                return g
    return None


def create_or_get(client):
    g = find(client)
    if g:
        return g["id"], g["version"] if g["version"] != "DRAFT" else _latest_version(client, g["id"])
    created = client.create_guardrail(
        name=NAME,
        description="Blocks fraud accusations and investment advice in statement summaries.",
        topicPolicyConfig={"topicsConfig": [
            {"name": "fraud accusations",
             "definition": "Statements that accuse a person or organization of fraud, theft, scams or "
                           "financial exploitation, or that call a transaction fraudulent.",
             "examples": ["This looks like fraud.", "Someone is stealing from you.",
                          "That wire was a scam."],
             "type": "DENY"},
            {"name": "investment advice",
             "definition": "Recommendations to buy, sell or hold any security or to change an "
                           "investment strategy.",
             "examples": ["You should sell your bonds.", "I recommend buying more stock.",
                          "Hold your IRA positions."],
             "type": "DENY"},
        ]},
        blockedInputMessaging=BLOCKED,
        blockedOutputsMessaging=BLOCKED,
    )
    version = client.create_guardrail_version(guardrailIdentifier=created["guardrailId"])["version"]
    return created["guardrailId"], version


def _latest_version(client, gid):
    versions = [g["version"] for p in client.get_paginator("list_guardrails").paginate(guardrailIdentifier=gid)
                for g in p["guardrails"] if g["version"] != "DRAFT"]
    return max(versions, key=int) if versions else client.create_guardrail_version(
        guardrailIdentifier=gid)["version"]


def test_blocks_advice(gid, version):
    rt = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    prompt = "Should I sell my IRA bonds and buy tech stocks? Tell me exactly what to buy."
    r = rt.apply_guardrail(guardrailIdentifier=gid, guardrailVersion=version, source="INPUT",
                           content=[{"text": {"text": prompt}}])
    return r["action"] == "GUARDRAIL_INTERVENED"


if __name__ == "__main__":
    c = _client()
    gid, ver = create_or_get(c)
    print(f"GUARDRAIL_ID={gid}\nGUARDRAIL_VERSION={ver}")
    if "--test" in sys.argv:
        ok = test_blocks_advice(gid, ver)
        print("PASS investment-advice prompt blocked" if ok else "FAIL advice prompt was not blocked")
        sys.exit(0 if ok else 1)
