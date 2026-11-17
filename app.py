"""Serve the local dashboard and execute one run at a time."""

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlsplit

from workbench import ROOT, RUNS, WORKBENCH_URL, list_runs, profiles, read_run, start_run

HOST = "127.0.0.1"
PORT = 8765
RUN_LOCK = Lock()
STATIC = {
    "/": ROOT / "web/index.html",
    "/style.css": ROOT / "web/style.css",
    "/app.js": ROOT / "web/app.js",
    "/demo/": ROOT / "demo/index.html",
    "/demo/style.css": ROOT / "demo/style.css",
    "/demo/checkout.js": ROOT / "demo/checkout.js",
}


class Handler(BaseHTTPRequestHandler):
    def send_body(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        self.send_body(json.dumps(value).encode(), "application/json", status)

    def valid_host(self):
        if self.headers.get("Host") == f"{HOST}:{PORT}":
            return True
        self.send_json({"error": f"Open {WORKBENCH_URL} directly."}, 403)
        return False

    def do_GET(self):
        if not self.valid_host():
            return
        path = urlsplit(self.path).path
        try:
            if path in STATIC:
                file = STATIC[path]
                self.send_body(file.read_bytes(), mimetypes.guess_type(file)[0])
            elif path == "/api/profiles":
                self.send_json(profiles())
            elif path == "/api/runs":
                self.send_json(list_runs())
            elif match := re.fullmatch(r"/api/runs/([0-9a-f]{32})", path):
                self.send_json(read_run(match[1]))
            elif match := re.fullmatch(r"/evidence/([0-9a-f]{32})/(check-[0-9]+\.png)", path):
                file = RUNS / match[1] / match[2]
                self.send_body(file.read_bytes(), "image/png")
            else:
                self.send_json({"error": "Not found."}, 404)
        except FileNotFoundError:
            self.send_json({"error": "Not found."}, 404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)

    def do_POST(self):
        if not self.valid_host():
            return
        if self.path != "/api/runs":
            self.send_json({"error": "Not found."}, 404)
            return
        if (self.headers.get("Origin") != WORKBENCH_URL or
                self.headers.get_content_type() != "application/json"):
            self.send_json({"error": "Use the local dashboard to start a run."}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2048:
                raise ValueError("Invalid request length.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected a profile name.")
            selected = next(
                (profile for profile in profiles() if profile["name"] == payload.get("profile")),
                None,
            )
            if selected is None:
                raise ValueError("Unknown profile.")
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
            return

        if not RUN_LOCK.acquire(blocking=False):
            self.send_json({"error": "A run is already in progress."}, 409)
            return
        try:
            self.send_json(start_run(selected), 201)
        finally:
            RUN_LOCK.release()


if __name__ == "__main__":
    with ThreadingHTTPServer((HOST, PORT), Handler) as server:
        print(f"QA Workbench is ready at {WORKBENCH_URL}. Stop with Ctrl+C.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
