"""A local fake of the Yandex Disk API + storage hosts, with scriptable failures."""
import hashlib
import http.server
import json
import threading
import time
import urllib.parse


class FakeYandex:
    """files: {"disk:/a/b.txt": bytes}.  plan: {"disk:/a/b.txt": ["empty", "500", "stall", "corrupt", ...]}

    Each storage request for a file consumes one entry of its plan; once exhausted the file is served
    normally. "empty" = 206 with no body (what sick Yandex storage hosts did), "500" = server error,
    "stall" = sleeps longer than the client's io timeout, "corrupt" = flips a byte.
    `delay` slows every storage response (useful to test pause/stop).
    """

    def __init__(self, files, plan=None, token="T0KEN", stall_seconds=2.0, delay=0.0):
        self.files = dict(files)
        self.plan = {k: list(v) for k, v in (plan or {}).items()}
        self.token = token
        self.stall_seconds = stall_seconds
        self.delay = delay
        self.lock = threading.Lock()
        self.bytes_served = 0
        self.requests = {}
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *a):
                pass

            def _json(self, obj, code=200):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(u.query)
                if u.path.startswith("/data"):
                    return outer._serve_data(self, q["p"][0])
                if u.path.startswith("/v1/disk/public/"):
                    return outer._public(self, u.path, q)
                if self.headers.get("Authorization") != "OAuth " + outer.token:
                    return self._json({"error": "unauthorized"}, 401)
                if u.path == "/v1/disk":
                    return self._json({"total_space": 10 ** 12, "used_space": 10 ** 9})
                if u.path == "/v1/disk/resources/files":
                    items = [{"path": p, "name": p.rsplit("/", 1)[-1], "size": len(b),
                              "md5": hashlib.md5(b).hexdigest()} for p, b in sorted(outer.files.items())]
                    off, lim = int(q.get("offset", [0])[0]), int(q.get("limit", [1000])[0])
                    return self._json({"items": items[off:off + lim]})
                if u.path == "/v1/disk/resources":
                    return outer._resources(self, q)
                if u.path == "/v1/disk/resources/download":
                    p = q["path"][0]
                    if p not in outer.files:
                        return self._json({"error": "not found"}, 404)
                    href = f"http://127.0.0.1:{outer.port}/data?p=" + urllib.parse.quote(p)
                    return self._json({"href": href})
                self._json({"error": "unknown"}, 404)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}/v1/disk"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    PUBLIC_LINK = "https://disk.yandex.ru/d/TESTLINK"

    def _public(self, h, upath, q):
        """Shared-link API: no token, paths relative to the link root ("/" = disk:/)."""
        if q.get("public_key", [""])[0] != self.PUBLIC_LINK:
            return h._json({"error": "not found"}, 404)
        p = q.get("path", ["/"])[0]
        internal = "disk:" + (p if p != "/" else "/")
        if upath.endswith("/download"):
            if internal not in self.files:
                return h._json({"error": "not found"}, 404)
            return h._json({"href": f"http://127.0.0.1:{self.port}/data?p=" + urllib.parse.quote(internal)})
        q = dict(q, path=[internal])
        return self._resources(h, q, public=True)

    def _resources(self, h, q, public=False):
        if public:
            real = h

            class _H:
                @staticmethod
                def _json(obj, code=200):
                    if code == 200:
                        obj = json.loads(json.dumps(obj).replace('"disk:/', '"/'))
                    real._json(obj, code)
            h = _H
        path = q["path"][0].rstrip("/") or "disk:"
        if path == "disk:":
            path = "disk:/"
        if path in self.files:
            b = self.files[path]
            return h._json({"type": "file", "path": path, "name": path.rsplit("/", 1)[-1], "size": len(b),
                            "md5": hashlib.md5(b).hexdigest()})
        prefix = path.rstrip("/") + "/"
        kids = {}
        for p, b in self.files.items():
            if p.startswith(prefix):
                head, _, rest = p[len(prefix):].partition("/")
                if rest:
                    kids[head] = {"type": "dir", "name": head, "path": prefix + head}
                else:
                    kids[head] = {"type": "file", "name": head, "path": p, "size": len(b),
                                  "md5": hashlib.md5(b).hexdigest()}
        if not kids:
            return h._json({"error": "not found"}, 404)
        items = sorted(kids.values(), key=lambda i: i["name"])
        off, lim = int(q.get("offset", [0])[0]), int(q.get("limit", [100])[0])
        return h._json({"type": "dir", "path": path, "name": path.rsplit("/", 1)[-1],
                        "_embedded": {"items": items[off:off + lim], "total": len(items)}})

    def _serve_data(self, h, path):
        if self.delay:
            time.sleep(self.delay)
        with self.lock:
            self.requests[path] = self.requests.get(path, 0) + 1
            behaviour = self.plan.get(path, []).pop(0) if self.plan.get(path) else "ok"
        data = self.files[path]
        rng = h.headers.get("Range", "")
        start, end = 0, len(data) - 1
        if rng.startswith("bytes="):
            a, b = rng[6:].split("-")
            start = int(a)
            end = min(int(b), len(data) - 1) if b else len(data) - 1
        if behaviour == "500":
            h.send_response(500)
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        if behaviour == "empty":
            h.send_response(206)
            h.end_headers()          # HTTP/1.0: body ends when the connection closes -> zero bytes
            return
        if behaviour == "stall":
            time.sleep(self.stall_seconds)
            return
        chunk = data[start:end + 1]
        if behaviour == "corrupt" and chunk:
            chunk = bytes([chunk[0] ^ 0xFF]) + chunk[1:]
        h.send_response(206 if rng else 200)
        h.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        h.send_header("Content-Length", str(len(chunk)))
        h.end_headers()
        h.wfile.write(chunk)
        with self.lock:
            self.bytes_served += len(chunk)
