"""One Lambda handler routing the six API endpoints (tested on sample data).

API Gateway proxy integration. Routes:
  POST /process               {"filename": "problem.pdf"} or a multipart/raw upload
  GET  /statement/{id}
  GET  /summary/{id}
  GET  /flags[?statement_id=]
  POST /flags/{id}/decision   {"action": "approve|escalate|dismiss", "note": "..."}
  GET  /audit/{id}

Demo scope: only the sample statements (data/ground_truth/<id>.json) are supported.
Env: STORE, SUMMARY_MOCK=1 (template summary, no Bedrock), AUDIO_BUCKET (if unset,
audio_url is null), plus those read by backend.summary.*.
"""
import base64
import json
import os
import re

from backend.api import decisions
from backend.common import store
from backend.flags.run import run_flags

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GT_DIR = os.path.join(ROOT, "data", "ground_truth")
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}
_summary_cache = {}


class HttpError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def _resp(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json", **CORS},
            "body": json.dumps(body)}


def known_ids():
    return sorted(f[:-5] for f in os.listdir(GT_DIR) if f.endswith(".json"))


def _statement(sid):
    if sid.startswith('upload-'):
        from backend.api import uploads
        try:
            return uploads.load(sid)
        except KeyError:
            raise HttpError(404, 'unknown uploaded statement')
    if sid not in known_ids():
        raise HttpError(404, f"unknown statement '{sid}'")
    with open(os.path.join(GT_DIR, f"{sid}.json")) as fh:
        return json.load(fh)


def _body_text(event):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("latin-1")
    return body


def _upload_filename(event):
    body = _body_text(event)
    try:
        data = json.loads(body)
        if isinstance(data, dict) and data.get("filename"):
            return str(data["filename"])
    except ValueError:
        pass
    m = re.search(r'filename="([^"]+)"', body)  # multipart upload
    if m:
        return m.group(1)
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    m = re.search(r'filename="?([^";]+)', headers.get("content-disposition", ""))
    return m.group(1) if m else None


def process(event):
    from backend.api import uploads
    try:
        pdf = uploads.uploaded_pdf(event)
        if pdf is not None:
            sid, statement = uploads.extract(pdf)
            flags = run_flags(sid, statement)
            return 200, {'statement_id': sid, 'flags_created': len(flags), 'extraction': 'textract',
                         'notice': 'Tested on sample data. New payee history is limited to this statement.'}
    except uploads.UploadError as error:
        raise HttpError(400, str(error))
    name = _upload_filename(event)
    sid = os.path.splitext(os.path.basename(name or ""))[0].lower()
    if sid not in known_ids():
        raise HttpError(400, "demo supports sample statements only")
    flags = run_flags(sid)
    return 200, {"statement_id": sid, "flags_created": len(flags)}


_SUPPORTED_LANGS = {"en", "es"}


def summary(sid, lang="en"):
    if lang not in _SUPPORTED_LANGS:
        raise HttpError(400, f"unsupported lang '{lang}'; supported: en, es")
    cache_key = (sid, lang)
    if cache_key not in _summary_cache:
        from backend.summary.summarize import summarize
        stmt = _statement(sid)
        result = {
            'statement_id': sid,
            **summarize(stmt, mock=os.environ.get('SUMMARY_MOCK') == '1', lang=lang),
        }
        result["audio_url"] = None
        if os.environ.get("AUDIO_BUCKET"):
            try:
                from backend.summary.speak import speak
                result["audio_url"] = speak(sid, result["text"], lang=lang)
            except Exception as e:  # read-aloud must never break the summary
                print(f"speak failed: {e}")
        _summary_cache[cache_key] = result
    return 200, _summary_cache[cache_key]


def decision(flag_id, event):
    try:
        data = json.loads(_body_text(event) or "{}")
    except ValueError:
        raise HttpError(400, "body must be JSON")
    try:
        return 200, decisions.decide(flag_id, data.get("action"), data.get("note", ""))
    except decisions.DecisionError as e:
        raise HttpError(400, str(e))
    except KeyError:
        raise HttpError(404, f"unknown flag '{flag_id}'")
    except decisions.ConflictError as e:
        raise HttpError(409, str(e))


def route(event):
    method = event.get("httpMethod", "GET").upper()
    path = "/" + (event.get("path") or "/").strip("/")
    q = event.get("queryStringParameters") or {}
    if method == "POST" and path == "/process":
        return process(event)
    if method == "GET" and path == "/flags":
        return 200, store.list_flags(q.get("statement_id"))
    m = re.fullmatch(r"/flags/([^/]+)/decision", path)
    if method == "POST" and m:
        return decision(m.group(1), event)
    m = re.fullmatch(r"/(statement|summary|audit)/([^/]+)", path)
    if method == "GET" and m:
        kind, sid = m.groups()
        if kind == "statement":
            return 200, _statement(sid)
        if kind == "summary":
            _statement(sid)
            return summary(sid, lang=q.get("lang", "en"))
        _statement(sid)
        return 200, decisions.get_audit(sid)
    raise HttpError(404, "not found")


def handler(event, context=None):
    if event.get("httpMethod", "").upper() == "OPTIONS":
        return {"statusCode": 204, "headers": CORS, "body": ""}
    try:
        status, body = route(event)
        return _resp(status, body)
    except HttpError as e:
        return _resp(e.status, {"error": e.message})
    except Exception as e:
        print(f"unhandled error: {e!r}")
        return _resp(500, {"error": "internal error"})
