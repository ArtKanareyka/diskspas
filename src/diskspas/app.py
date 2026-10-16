"""Application controller behind the web UI: login, browsing, scanning, running and controlling a download."""
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time

from . import __version__, auth
from .api import DEFAULT_BASE, PUBLIC_BASE, Api, ApiError, AuthError, NotFound, PublicApi, normalize_public_link
from .engine import Engine
from .paths import local_path
from .priority import tier
from .state import StateStore

# Set after the OAuth app is verified so ordinary users can skip app creation.
DEFAULT_CLIENT_ID = ""
# Link for the "Help" button in the window (for example the repository issues page). Empty = no button.
DEFAULT_SUPPORT_URL = "https://github.com/ArtKanareyka/diskspas/issues/new/choose"


class AppError(Exception):
    def __init__(self, message, code="error"):
        super().__init__(message)
        self.code = code


class App:
    def __init__(self, api_base=None, client_id=None, cfg_dir=None, engine_kw=None):
        self.api_base = api_base or os.environ.get("YADISK_API_BASE", DEFAULT_BASE)
        self.public_base = os.environ.get("YADISK_PUBLIC_BASE", PUBLIC_BASE) if not api_base else api_base.rstrip("/") + "/public"
        self.cfg_dir = cfg_dir or auth.config_dir()
        os.makedirs(self.cfg_dir, exist_ok=True)
        self.engine_kw = engine_kw or {}
        self.settings = self._load_settings()
        self.client_id = (client_id or os.environ.get("YADISK_RESCUE_CLIENT_ID")
                          or self.settings.get("client_id") or DEFAULT_CLIENT_ID)
        self.key = secrets.token_urlsafe(18)       # required header for every API call
        self.lock = threading.RLock()
        self.shutdown = threading.Event()
        self.last_seen = time.time()

        self.api = None
        self.disk = None
        self.public = None      # {"name", "link"} when working from a shared link
        self.scan_state = {"state": "idle", "count": 0, "error": ""}
        self.plan_items = None
        self.plan = None
        self.engine = None
        self.thread = None
        self.dest = ""
        link = self.settings.get("public_link")
        if link:                                   # last session was from a shared link
            try:
                self.login_public(link)
            except AppError:
                self.settings.pop("public_link", None)
        token = auth.load_token(self.cfg_dir)
        if token and self.api is None:
            self._try_token(token)

    # ---- settings -------------------------------------------------------
    @property
    def _settings_path(self):
        return os.path.join(self.cfg_dir, "settings.json")

    def _load_settings(self):
        try:
            with open(self._settings_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_settings(self, **kw):
        self.settings.update({k: v for k, v in kw.items() if v is not None})
        tmp = self._settings_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.settings, f)
        os.replace(tmp, self._settings_path)

    def _forget_public(self):
        if self.settings.pop("public_link", None) is not None:
            self.save_settings()

    def save_prefs(self, prefs):
        """Remember the UI choices (selection, junk, threads...) between launches."""
        prefs = prefs if isinstance(prefs, dict) else {}
        sel = [str(x) for x in (prefs.get("selection") or [])][:5000]
        self.save_settings(prefs={"mode": "select" if prefs.get("mode") == "select" else "all", "selection": sel,
                                  "skip_junk": bool(prefs.get("skip_junk")), "verify": bool(prefs.get("verify", True)),
                                  "max_threads": max(4, min(256, int(prefs.get("max_threads") or 128)))})
        return {"ok": True}

    # ---- login ------------------------------------------------------------
    def _try_token(self, token):
        api = Api(token, base=self.api_base)
        try:
            info = api.disk_info()
        except AuthError:
            return False
        except ApiError:
            return False
        with self.lock:
            self.api, self.disk = api, {"total": info.get("total_space", 0), "used": info.get("used_space", 0)}
        return True

    def login(self, token, client_id=None):
        token = (token or "").strip()
        if not token:
            raise AppError("Пустой токен", "empty_token")
        if not self._try_token(token):
            raise AppError("Яндекс не принял этот токен", "bad_token")
        auth.save_token(token, self.cfg_dir)
        self._forget_public()
        if client_id:
            self.client_id = client_id.strip()
            self.save_settings(client_id=self.client_id)
        return self.status()

    def login_public(self, link):
        url = normalize_public_link(link)
        if not url:
            raise AppError("Это не похоже на ссылку Яндекс Диска", "bad_link")
        api = PublicApi(url, base=self.public_base)
        try:
            info = api.info()
        except NotFound:
            raise AppError("По этой ссылке ничего нет: она удалена или закрыта", "link_gone")
        except ApiError as e:
            raise AppError(f"Не удалось открыть ссылку: {e}", "link_failed")
        with self.lock:
            self.api, self.disk, self.public = api, None, {"name": info["name"], "link": url}
            self.plan = self.plan_items = None
        self.save_settings(public_link=url)
        return self.status()

    def logout(self):
        if self.running():
            raise AppError("Сначала остановите загрузку", "busy")
        if self.public is None:
            auth.delete_token(self.cfg_dir)
        else:
            self._forget_public()
        with self.lock:
            self.api = self.disk = self.public = self.plan = self.plan_items = None
            self.engine = None
        return self.status()

    # ---- state ----------------------------------------------------------------
    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def status(self):
        with self.lock:
            st = {
                "version": __version__, "logged_in": self.api is not None, "disk": self.disk, "public": self.public,
                "client_id_set": bool(self.client_id), "client_id": self.client_id,
                "support_url": os.environ.get("DISKSPAS_SUPPORT_URL") or self.settings.get("support_url") or DEFAULT_SUPPORT_URL,
                "authorize_url": auth.authorize_url(self.client_id) if self.client_id else "",
                "dest": self.dest or self.settings.get("dest", ""), "scan": dict(self.scan_state),
                "prefs": self.settings.get("prefs"), "plan": self.plan, "running": self.running(), "job": None, "os": os.name,
            }
        eng = self.engine
        if eng is not None:
            st["job"] = eng.snapshot()
        return st

    def _need_login(self):
        if self.api is None:
            raise AppError("Нужно войти в аккаунт", "not_logged_in")
        return self.api

    # ---- Yandex Disk browsing -------------------------------------------
    def tree(self, path):
        api = self._need_login()
        if self.public is not None:
            path = "/" if (path or "disk:/") in ("disk:/", "disk:") else path
        return api.list_dir(path or "disk:/")

    # ---- local folder browsing ---------------------------------------------
    def _roots(self):
        home = os.path.expanduser("~")
        quick = []
        for name, title in (("Desktop", "Рабочий стол"), ("Documents", "Документы"),
                            ("Downloads", "Загрузки"), ("Pictures", "Изображения")):
            p = os.path.join(home, name)
            if os.path.isdir(p):
                quick.append({"name": title, "path": p})
        quick.insert(0, {"name": "Домашняя папка", "path": home})
        drives = []
        if os.name == "nt":
            try:
                import ctypes
                mask = ctypes.windll.kernel32.GetLogicalDrives()
                drives = [{"name": f"{chr(65 + i)}:", "path": f"{chr(65 + i)}:\\"} for i in range(26) if mask >> i & 1]
            except Exception:
                pass
        else:
            drives = [{"name": "/", "path": "/"}]
            for base in ("/Volumes", "/mnt", "/media"):
                if os.path.isdir(base):
                    try:
                        drives += [{"name": e, "path": os.path.join(base, e)} for e in sorted(os.listdir(base))]
                    except OSError:
                        pass
        return {"path": "", "parent": None, "dirs": [], "roots": drives, "quick": quick, "free": None}

    def fs(self, path):
        if not path:
            return self._roots()
        p = os.path.abspath(path)
        if not os.path.isdir(p):
            raise AppError("Такой папки нет", "no_folder")
        dirs = []
        try:
            for e in os.scandir(p):
                try:
                    if e.is_dir(follow_symlinks=False) and not e.name.startswith("."):
                        dirs.append(e.name)
                except OSError:
                    pass
        except OSError as e:
            raise AppError(f"Не удалось открыть папку: {e.strerror or e}", "denied")
        dirs.sort(key=str.lower)
        parent = os.path.dirname(p)
        try:
            free = shutil.disk_usage(p).free
        except OSError:
            free = None
        return {"path": p, "parent": parent if parent != p else "", "dirs": dirs, "free": free}

    def mkdir(self, parent, name):
        name = (name or "").strip()
        if not name or any(c in name for c in '\\/:*?"<>|') or name in (".", ".."):
            raise AppError("Недопустимое имя папки", "bad_name")
        target = os.path.join(os.path.abspath(parent), name)
        try:
            os.makedirs(target, exist_ok=True)
        except OSError as e:
            raise AppError(f"Не удалось создать папку: {e.strerror or e}", "denied")
        return self.fs(target)

    def open_folder(self, path):
        if not os.path.isdir(path):
            raise AppError("Такой папки нет", "no_folder")
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            raise AppError(f"Не удалось открыть папку: {e}", "open_failed")
        return {"ok": True}

    # ---- scanning the selection ---------------------------------------------
    def start_scan(self, selection, skip_junk=False):
        api = self._need_login()
        if self.running():
            raise AppError("Загрузка уже идёт", "busy")
        with self.lock:
            if self.scan_state["state"] == "scanning":
                raise AppError("Сканирование уже идёт", "busy")
            self.scan_state = {"state": "scanning", "count": 0, "error": ""}
            self.plan = self.plan_items = None
        sel = [s for s in (selection or []) if s]
        whole = not sel or any(s.rstrip("/") in ("disk:", "") for s in sel)
        if self.public is not None and whole:
            sel, whole = ["/"], False

        def progress(n):
            self.scan_state["count"] = n

        def work():
            try:
                if whole:
                    items = api.list_files(progress)
                else:
                    seen, items = set(), []
                    for s in sel:
                        for it in api.list_tree(s):
                            if it["path"] not in seen:
                                seen.add(it["path"])
                                items.append(it)
                                progress(len(items))
                junk = [i for i in items if tier(i["path"], int(i.get("size") or 0)) == 2]
                if skip_junk:
                    jp = {i["path"] for i in junk}
                    items = [i for i in items if i["path"] not in jp]
                total = sum(int(i.get("size") or 0) for i in items)
                with self.lock:
                    self.plan_items = items
                    self.plan = {"files": len(items), "bytes": total, "junk_files": len(junk),
                                 "junk_bytes": sum(int(i.get("size") or 0) for i in junk), "skipped_junk": bool(skip_junk)}
                    self.scan_state = {"state": "done", "count": len(items), "error": ""}
            except Exception as e:
                with self.lock:
                    self.scan_state = {"state": "error", "count": 0, "error": str(e)[:300]}

        threading.Thread(target=work, daemon=True).start()
        return {"ok": True}

    def remaining(self, dest):
        """Bytes still to download into `dest`: files already there (and partial .part files) don't count."""
        if self.plan_items is None:
            raise AppError("Сначала просканируйте Диск", "no_plan")
        dest = os.path.abspath((dest or "").strip() or ".")
        prefix = "" if self.public is not None else "disk:"
        need = already = 0
        for it in self.plan_items:
            size = int(it.get("size") or 0)
            path = it["path"]
            rel = path[len(prefix):].lstrip("/") if path.startswith(prefix) else it["name"]
            out = local_path(dest, rel)
            try:
                if os.path.getsize(out) == size:
                    already += size
                    continue
            except OSError:
                pass
            try:
                have = min(os.path.getsize(out + ".part"), size)
            except OSError:
                have = 0
            already += have
            need += size - have
        return {"need": need, "already": already, "free": shutil.disk_usage(dest).free if os.path.isdir(dest) else None}

    # ---- running a download ------------------------------------------------------
    def start(self, dest, options=None):
        api = self._need_login()
        opts = options or {}
        if self.running():
            raise AppError("Загрузка уже идёт", "busy")
        if self.plan_items is None:
            raise AppError("Сначала просканируйте Диск", "no_plan")
        raw = (dest or "").strip()
        if not raw:                      # abspath("") would silently mean "the current folder"
            raise AppError("Выберите папку для сохранения", "no_dest")
        dest = os.path.abspath(raw)
        if os.path.dirname(dest) == dest:
            raise AppError("Выберите папку, а не весь диск целиком", "root_dest")
        try:
            os.makedirs(dest, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=dest):
                pass
        except OSError as e:
            raise AppError(f"В эту папку нельзя записать: {e.strerror or e}", "denied")
        need, free = self.remaining(dest)["need"], shutil.disk_usage(dest).free
        if need > free and not opts.get("force"):
            raise AppError(f"Не хватает места: нужно {need}, свободно {free}", "no_space")

        kw = dict(start_threads=int(opts.get("start_threads", 16)), min_threads=4,
                  max_threads=max(4, min(256, int(opts.get("max_threads", 128)))),
                  verify=bool(opts.get("verify", True)), state=StateStore(dest))
        kw.update(self.engine_kw)
        eng = Engine(api, dest, prefix="" if self.public is not None else "disk:", **kw)
        api.on_error = eng.log_err
        items = list(self.plan_items)

        def run():
            try:
                eng.run(items)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                eng.log_err(f"критическая ошибка: {type(e).__name__}: {e}")
                eng.phase = "error"
                eng.stop.set()

        with self.lock:
            self.engine, self.dest = eng, dest
            self.thread = threading.Thread(target=run, daemon=True)
            self.thread.start()
        self.save_settings(dest=dest)
        return self.status()

    def pause(self):
        if self.engine:
            self.engine.pause()
        return {"ok": True}

    def resume(self):
        if self.engine:
            self.engine.resume()
        return {"ok": True}

    def stop(self):
        if self.engine:
            self.engine.request_stop()
        return {"ok": True}

    def reset(self):
        """Forget a finished job so a new one can be configured."""
        if self.running():
            raise AppError("Загрузка уже идёт", "busy")
        with self.lock:
            self.engine = self.thread = self.plan = self.plan_items = None
            self.scan_state = {"state": "idle", "count": 0, "error": ""}
        return self.status()
