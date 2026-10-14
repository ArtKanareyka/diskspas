"""Local HTTP server for the UI.

Security: bound to 127.0.0.1 only; every /api call needs the per-run secret key (header X-Key) and a
matching Host header. A random website cannot call it: browsers cannot add the custom header cross-site
without a CORS preflight, which this server never approves, and DNS-rebinding fails the Host check.
"""
import hmac
import http.server
import json
import threading
import time
import urllib.parse

from .api import ApiError, AuthError
from .app import AppError
from .page import PAGE

GET = {
    "/api/ping": lambda app, q, b: {"ok": True, "app": "diskspas"},
    "/api/status": lambda app, q, b: app.status(),
    "/api/tree": lambda app, q, b: app.tree(q.get("path", ["disk:/"])[0]),
    "/api/fs": lambda app, q, b: app.fs(q.get("path", [""])[0]),
}


POST = {
    "/api/login": lambda app, q, b: app.login(b.get("token"), b.get("client_id")),
    "/api/login_public": lambda app, q, b: app.login_public(b.get("link")),
    "/api/logout": lambda app, q, b: app.logout(),
    "/api/scan": lambda app, q, b: app.start_scan(b.get("selection") or [], bool(b.get("skip_junk"))),
    "/api/start": lambda app, q, b: app.start(b.get("dest"), b.get("options")),
    "/api/pause": lambda app, q, b: app.pause(),
    "/api/resume": lambda app, q, b: app.resume(),
    "/api/stop": lambda app, q, b: app.stop(),
    "/api/reset": lambda app, q, b: app.reset(),
    "/api/mkdir": lambda app, q, b: app.mkdir(b.get("parent", ""), b.get("name", "")),
    "/api/open": lambda app, q, b: app.open_folder(b.get("path", "")),
}


def make_server(app, port=8765, tries=20):
    """Create the server on `port` (or the next free one). Returns the HTTPServer, not yet serving."""

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            pass

        def _send(self, code, payload, ctype="application/json; charset=utf-8"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self):
            p = self.server.server_address[1]
            return self.headers.get("Host", "") in (f"127.0.0.1:{p}", f"localhost:{p}")

        def _handle(self, method):
            if not self._host_ok():
                return self._send(403, {"error": "bad host", "code": "forbidden"})
            u = urllib.parse.urlparse(self.path)
            if u.path == "/":
                return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            if not u.path.startswith("/api/"):
                return self._send(404, {"error": "not found"})
            if not hmac.compare_digest(self.headers.get("X-Key", ""), app.key):
                return self._send(403, {"error": "forbidden", "code": "forbidden"})
            app.last_seen = time.time()
            fn = (GET if method == "GET" else POST).get(u.path)
            if fn is None:
                return self._send(404, {"error": "unknown endpoint"})
            try:
                body = {}
                if method == "POST":
                    n = int(self.headers.get("Content-Length") or 0)
                    body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                result = fn(app, urllib.parse.parse_qs(u.query), body)
                self._send(200, result)
            except AppError as e:
                self._send(400, {"error": str(e), "code": e.code})
            except AuthError as e:
                self._send(401, {"error": str(e), "code": "auth"})
            except ApiError as e:
                self._send(502, {"error": str(e), "code": "api"})
            except Exception as e:  # never leak details beyond the message
                self._send(500, {"error": f"{type(e).__name__}: {e}", "code": "internal"})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

    last = None
    for p in range(port, port + tries) if port else [0]:
        try:
            return http.server.ThreadingHTTPServer(("127.0.0.1", p), Handler)
        except OSError as e:
            last = e
    raise last


def serve_in_thread(server):
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t
