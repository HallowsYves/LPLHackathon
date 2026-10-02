"""Deployed smoke test (tested on sample data). Standard library only.

  python infra/e2e_test.py [API_BASE]     # or env API_BASE, or the value in frontend/config.js

Walks the demo: process `problem` (expect 3 flags), summary + audio URL (must return 200),
escalate without a note (must be refused), escalate with a note, read the audit trail.
Every request carries a browser-style Origin header and the responses must allow it (CORS),
and a preflight OPTIONS request must succeed. Prints PASS/FAIL per check; exit 1 on any FAIL.
Re-running is safe: /process resets the statement's flags to open.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

ORIGIN = "http://clear-statement-demo.example"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def base_url():
    if len(sys.argv) > 1:
        return sys.argv[1].rstrip("/")
    if os.environ.get("API_BASE"):
        return os.environ["API_BASE"].rstrip("/")
    try:
        text = open(os.path.join(ROOT, "frontend", "config.js")).read()
        m = re.search(r'API_BASE\s*=\s*"([^"]+)"', text)
        if m:
            return m.group(1).rstrip("/")
    except OSError:
        pass
    sys.exit("usage: python infra/e2e_test.py <API_BASE>")


def call(method, path, body=None, base=None, timeout=60):
    req = urllib.request.Request(base + path, method=method, headers={"Origin": ORIGIN},
                                 data=json.dumps(body).encode() if body is not None else None)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, headers, raw = r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        status, headers, raw = e.code, e.headers, e.read()
    return status, headers, (json.loads(raw) if raw else None)


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def main():
    base = base_url()
    print(f"API: {base}")
    pre = urllib.request.Request(base + "/flags", method="OPTIONS", headers={
        "Origin": ORIGIN, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    try:
        with urllib.request.urlopen(pre, timeout=30) as r:
            allow = r.headers.get("Access-Control-Allow-Origin")
            check("CORS preflight", r.status in (200, 204) and allow in ("*", ORIGIN), f"{r.status} {allow}")
    except Exception as e:
        check("CORS preflight", False, str(e))

    s, h, d = call("POST", "/process", {"filename": "problem.pdf"}, base)
    check("POST /process problem", s == 200 and d.get("statement_id") == "problem", f"{s} {d}")
    check("CORS header on response", h.get("Access-Control-Allow-Origin") in ("*", ORIGIN))
    s, _, d = call("POST", "/process", {"filename": "other.pdf"}, base)
    check("unknown upload refused", s == 400, f"{s}")
    s, _, flags = call("GET", "/flags?statement_id=problem", base=base)
    check("3 open flags", s == 200 and len(flags) == 3 and all(f["status"] == "open" for f in flags),
          f"{s} {flags}")
    s, _, st = call("GET", "/statement/problem", base=base)
    check("GET /statement/problem", s == 200 and st["client"]["name"] == "Margaret Hale", f"{s}")

    s, _, sm = call("GET", "/summary/problem", base=base, timeout=90)
    check("GET /summary text", s == 200 and bool(sm.get("text")), f"{s}")
    v = (sm or {}).get("validation", {})
    check("summary validation has no mismatches", v.get("mismatches") == [] and v.get("figures_checked", 0) > 0, str(v))
    url = (sm or {}).get("audio_url")
    if url:
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                check("audio URL returns 200", r.status == 200 and "audio" in r.headers.get("Content-Type", ""), str(r.status))
        except Exception as e:
            check("audio URL returns 200", False, str(e))
    else:
        check("audio URL returns 200", False, "audio_url missing")

    wire = next((f for f in flags or [] if f["rule"] == "large_wire_new_payee"), None)
    if wire:
        s, _, d = call("POST", f"/flags/{wire['id']}/decision", {"action": "escalate"}, base)
        check("escalate without note refused", s == 400, f"{s}")
        s, _, d = call("POST", f"/flags/{wire['id']}/decision",
                       {"action": "escalate", "note": "e2e test: call client about the wire"}, base)
        check("escalate with note", s == 200 and d.get("action") == "escalate", f"{s} {d}")
        s, _, d = call("POST", f"/flags/{wire['id']}/decision", {"action": "dismiss", "note": "x"}, base)
        check("second decision refused", s == 409, f"{s}")
        s, _, audit = call("GET", "/audit/problem", base=base)
        check("audit trail has the decision",
              s == 200 and any(a["flag_id"] == wire["id"] and a["action"] == "escalate" for a in audit), f"{s}")
    else:
        check("wire flag present", False)

    ok = all(results)
    print("\nPASS (tested on sample data)" if ok else "\nFAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
