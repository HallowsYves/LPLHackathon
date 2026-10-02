"""Run the API locally for the frontend, no AWS needed (tested on sample data).

  python backend/api/local_server.py [--mock] [--port 8000]

Uses STORE=local unless STORE is set. --mock uses the template summary (no Bedrock)
and skips audio unless AUDIO_BUCKET is set.
"""
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("STORE", "local")

from backend.api.handler import handler  # noqa: E402


class Local(BaseHTTPRequestHandler):
    def _go(self):
        url = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        event = {"httpMethod": self.command, "path": url.path,
                 "queryStringParameters": dict(parse_qsl(url.query)) or None,
                 "headers": dict(self.headers),
                 "body": self.rfile.read(length).decode("latin-1") if length else None}
        r = handler(event)
        body = r["body"].encode()
        self.send_response(r["statusCode"])
        for k, v in r["headers"].items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_OPTIONS = _go

    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")


if __name__ == "__main__":
    if "--mock" in sys.argv:
        os.environ["SUMMARY_MOCK"] = "1"
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    print(f"Clear Statement API on http://localhost:{port} (STORE={os.environ['STORE']})")
    ThreadingHTTPServer(("localhost", port), Local).serve_forever()
