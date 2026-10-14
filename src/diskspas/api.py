"""Minimal Yandex Disk REST API client (standard library only)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://cloud-api.yandex.net/v1/disk"


class ApiError(Exception):
    pass


class AuthError(ApiError):
    """Token rejected (401/403)."""


class NotFound(ApiError):
    pass


class Api:
    def __init__(self, token, base=DEFAULT_BASE, timeout=60.0, sleep=time.sleep, on_error=None):
        self.token = token
        self.base = base.rstrip("/")
        self.timeout = timeout
        self._sleep = sleep
        self.on_error = on_error or (lambda msg: None)

    def _headers(self):
        return {"Authorization": "OAuth " + self.token}

    def _denied(self, code):
        return AuthError(f"HTTP {code}: токен отклонён или у него нет права cloud_api:disk.read")

    def _get(self, endpoint, **params):
        url = self.base + endpoint + "?" + urllib.parse.urlencode(params)
        last = None
        for attempt in range(8):
            try:
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise self._denied(e.code) from None
                if e.code == 404:
                    raise NotFound(params.get("path", endpoint)) from None
                last = e
            except Exception as e:  # timeouts, resets, DNS, bad JSON
                last = e
            self.on_error(f"api {endpoint}: {last}")
            self._sleep(min(60, 2 ** attempt))
        raise ApiError(f"Яндекс не ответил после нескольких попыток ({endpoint}): {last}")

    def disk_info(self):
        return self._get("")

    def list_files(self, progress=None):
        """Every file on the Disk (flat listing, fast: 1000 per request)."""
        out, offset = [], 0
        while True:
            d = self._get("/resources/files", limit=1000, offset=offset,
                          fields="items.path,items.name,items.size,items.md5")
            items = d.get("items", [])
            out.extend(items)
            if progress:
                progress(len(out))
            if len(items) < 1000:
                return out
            offset += 1000

    def list_tree(self, path, progress=None):
        """Files under one folder (or a single file) via recursive listing."""
        out = []

        def walk(p):
            offset = 0
            while True:
                d = self._get("/resources", path=p, limit=200, offset=offset,
                              fields="type,path,name,size,md5,_embedded.items.type,_embedded.items.path,"
                                     "_embedded.items.name,_embedded.items.size,_embedded.items.md5,"
                                     "_embedded.total")
                if d["type"] == "file":
                    out.append(d)
                    return
                emb = d["_embedded"]
                for it in emb["items"]:
                    if it["type"] == "dir":
                        walk(it["path"])
                    else:
                        out.append(it)
                if progress:
                    progress(len(out))
                offset += 200
                if offset >= emb["total"]:
                    return

        walk(path)
        return out

    def list_dir(self, path, max_items=20000):
        """Immediate children of one Disk folder: [{name, path, type, size}], folders first."""
        out, offset = [], 0
        while True:
            d = self._get("/resources", path=path, limit=500, offset=offset,
                          fields="type,_embedded.items.name,_embedded.items.path,_embedded.items.type,"
                                 "_embedded.items.size,_embedded.total")
            emb = d.get("_embedded", {})
            items = emb.get("items", [])
            out.extend(items)
            offset += 500
            if not items or offset >= emb.get("total", 0) or len(out) >= max_items:
                break
        out.sort(key=lambda i: (i.get("type") != "dir", i.get("name", "").lower()))
        return [{"name": i["name"], "path": i["path"], "type": i["type"], "size": i.get("size", 0)} for i in out]

    def download_href(self, path):
        return self._get("/resources/download", path=path)["href"]


PUBLIC_BASE = "https://cloud-api.yandex.net/v1/disk/public"


class PublicApi(Api):
    """Same interface for a shared link (disk.yandex.ru/d/...): no token, paths are relative to the link root."""

    def __init__(self, link, base=PUBLIC_BASE, **kw):
        super().__init__(None, base=base, **kw)
        self.link = link
        self._single = False

    def _headers(self):
        return {}

    def _denied(self, code):
        return ApiError(f"HTTP {code}: владелец закрыл ссылку или превышен лимит скачивания")

    def _get(self, endpoint, **params):
        return super()._get(endpoint, public_key=self.link, **params)

    def info(self):
        d = self._get("/resources", path="/", limit=0, fields="name,type,size")
        return {"name": d.get("name", ""), "type": d.get("type", "dir")}

    def list_tree(self, path, progress=None):
        out = super().list_tree(path, progress)
        if len(out) == 1 and out[0].get("path") in ("/", None):   # a link to one file
            self._single = True
            out[0]["path"] = "/" + out[0]["name"]
        return out

    def list_files(self, progress=None):
        return self.list_tree("/", progress)

    def download_href(self, path):
        if self._single:
            return self._get("/resources/download")["href"]
        return self._get("/resources/download", path=path)["href"]


def normalize_public_link(text):
    """Accept what people paste: a link, possibly with spaces/newlines. Returns '' if it is not a Disk link."""
    link = (text or "").strip().split()[0] if (text or "").strip() else ""
    host = urllib.parse.urlparse(link).netloc.lower()
    if host.split(":")[0] in ("disk.yandex.ru", "disk.yandex.com", "yadi.sk", "disk.360.yandex.ru"):
        return link
    return ""
