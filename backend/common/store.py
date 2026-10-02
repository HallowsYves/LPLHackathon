"""Flag and audit storage with a local/DynamoDB switch (tested on sample data).

STORE=local  (default): JSON files under .local_store/ at the repo root
                        (override the folder with LOCAL_STORE_DIR).
STORE=dynamo: DynamoDB tables cs_flags (key id) and cs_audit (key id);
              region from AWS_REGION. Lists use scans with a filter, which is
              fine at demo scale.

Flag ids (f1, f2, ...) are unique per statement run, so save_flags replaces
every flag of a statement and callers should not mix statements with the same ids.
Run `python -m backend.common.store` for a round-trip self check on the
configured backend.
"""
import json
import os

FLAGS_TABLE = "cs_flags"
AUDIT_TABLE = "cs_audit"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _backend():
    return os.environ.get("STORE", "local").lower()


# ---------- public API ----------

def save_flags(statement_id, flags):
    """Replace all stored flags for statement_id with `flags` (idempotent)."""
    flags = [{**f, "statement_id": statement_id} for f in flags]
    return (_dyn_save_flags if _backend() == "dynamo" else _loc_save_flags)(statement_id, flags)


def list_flags(statement_id=None):
    return (_dyn_list_flags if _backend() == "dynamo" else _loc_list_flags)(statement_id)


def get_flag(flag_id):
    """Return the flag dict, or None if it does not exist."""
    return (_dyn_get_flag if _backend() == "dynamo" else _loc_get_flag)(flag_id)


def update_flag_status(flag_id, status):
    """Set a flag's status and return the updated flag. Raises KeyError if missing."""
    return (_dyn_update if _backend() == "dynamo" else _loc_update)(flag_id, status)


def add_audit(record):
    """Store an audit record (id assigned as a1, a2, ... if absent) and return it."""
    return (_dyn_add_audit if _backend() == "dynamo" else _loc_add_audit)(dict(record))


def list_audit(statement_id):
    """Audit records for a statement, oldest first."""
    return (_dyn_list_audit if _backend() == "dynamo" else _loc_list_audit)(statement_id)


# ---------- local backend ----------

def _dir():
    d = os.environ.get("LOCAL_STORE_DIR") or os.path.join(ROOT, ".local_store")
    os.makedirs(d, exist_ok=True)
    return d


def _read(name):
    try:
        with open(os.path.join(_dir(), name)) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return []


def _write(name, rows):
    path = os.path.join(_dir(), name)
    with open(path + ".tmp", "w") as fh:
        json.dump(rows, fh, indent=2)
    os.replace(path + ".tmp", path)


def _loc_save_flags(statement_id, flags):
    rows = [f for f in _read("flags.json") if f.get("statement_id") != statement_id] + flags
    _write("flags.json", rows)
    return flags


def _loc_list_flags(statement_id):
    return [f for f in _read("flags.json") if statement_id is None or f.get("statement_id") == statement_id]


def _loc_get_flag(flag_id):
    return next((f for f in _read("flags.json") if f["id"] == flag_id), None)


def _loc_update(flag_id, status):
    rows = _read("flags.json")
    for f in rows:
        if f["id"] == flag_id:
            f["status"] = status
            _write("flags.json", rows)
            return f
    raise KeyError(flag_id)


def _next_audit_id(rows):
    nums = [int(r["id"][1:]) for r in rows if r.get("id", "")[1:].isdigit()]
    return f"a{max(nums, default=0) + 1}"


def _loc_add_audit(record):
    rows = _read("audit.json")
    record.setdefault("id", _next_audit_id(rows))
    _write("audit.json", rows + [record])
    return record


def _loc_list_audit(statement_id):
    return [r for r in _read("audit.json") if r.get("statement_id") == statement_id]


# ---------- DynamoDB backend ----------

def _table(name):
    import boto3  # imported lazily so the local backend needs no AWS libraries
    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION")).Table(name)


def _scan(name, statement_id=None):
    from boto3.dynamodb.conditions import Attr
    table, kwargs, items = _table(name), {}, []
    if statement_id is not None:
        kwargs["FilterExpression"] = Attr("statement_id").eq(statement_id)
    while True:
        page = table.scan(**kwargs)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _num_key(f):
    return (len(f["id"]), f["id"])


def _dyn_save_flags(statement_id, flags):
    table = _table(FLAGS_TABLE)
    with table.batch_writer() as batch:
        for old in _scan(FLAGS_TABLE, statement_id):
            batch.delete_item(Key={"id": old["id"]})
        for f in flags:
            batch.put_item(Item=f)
    return flags


def _dyn_list_flags(statement_id):
    return sorted(_scan(FLAGS_TABLE, statement_id), key=_num_key)


def _dyn_get_flag(flag_id):
    return _table(FLAGS_TABLE).get_item(Key={"id": flag_id}).get("Item")


def _dyn_update(flag_id, status):
    from botocore.exceptions import ClientError
    try:
        res = _table(FLAGS_TABLE).update_item(
            Key={"id": flag_id}, UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": status},
            ConditionExpression="attribute_exists(id)", ReturnValues="ALL_NEW")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise KeyError(flag_id) from None
        raise
    return res["Attributes"]


def _dyn_add_audit(record):
    if "id" not in record:
        record["id"] = _next_audit_id(_scan(AUDIT_TABLE))
    _table(AUDIT_TABLE).put_item(Item=record)
    return record


def _dyn_list_audit(statement_id):
    return sorted(_scan(AUDIT_TABLE, statement_id),
                  key=lambda r: (r.get("timestamp", ""), len(r["id"]), r["id"]))


# ---------- self check ----------

def _self_check():
    sid = "selfcheck"
    flags = [{"id": "f1", "rule": "fee_jump", "txn_ids": [], "reason": "Worth a call.",
              "status": "open", "created_at": "2026-10-03T00:00:00Z"}]
    saved = save_flags(sid, flags)
    assert saved[0]["statement_id"] == sid
    save_flags(sid, flags)  # idempotent: no duplicate
    assert [f["id"] for f in list_flags(sid)] == ["f1"], list_flags(sid)
    assert get_flag("f1")["status"] == "open"
    assert update_flag_status("f1", "escalated")["status"] == "escalated"
    assert get_flag("f1")["status"] == "escalated"
    assert get_flag("nope") is None
    try:
        update_flag_status("nope", "dismissed")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
    rec = add_audit({"statement_id": sid, "flag_id": "f1", "advisor": "Dana Ortiz (demo advisor)",
                     "action": "escalate", "note": "check", "timestamp": "2026-10-03T01:14:00Z"})
    assert rec["id"].startswith("a")
    assert [r["id"] for r in list_audit(sid)] == [rec["id"]]
    assert list_audit("other") == []
    save_flags(sid, [])  # clean up flags
    print(f"PASS store round trip ({_backend()} backend)")


if __name__ == "__main__":
    _self_check()
