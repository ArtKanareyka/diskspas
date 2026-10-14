"""Start the UI: local server + browser. Reuses an already running instance."""
import json
import os
import time
import urllib.request
import webbrowser

from . import auth
from .app import App
from .web import make_server, serve_in_thread

IDLE_EXIT = 3 * 60   # exit this long after the last UI request when nothing is downloading


def _say(msg):
    try:
        print(msg, flush=True)
    except Exception:
        pass


def _info_path(cfg):
    return os.path.join(cfg, "ui.json")


def _existing(cfg):
    """If another copy is running, return its URL (with key) so we just open it."""
    try:
        with open(_info_path(cfg), encoding="utf-8") as f:
            d = json.load(f)
        req = urllib.request.Request(f"http://127.0.0.1:{d['port']}/api/ping", headers={"X-Key": d["key"]})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            if json.load(r).get("app") == "diskspas":
                return f"http://127.0.0.1:{d['port']}/#k={d['key']}"
    except Exception:
        pass
    return None


def run_ui(port=8765, open_browser=True, cfg_dir=None, app=None):
    cfg = cfg_dir or auth.config_dir()
    os.makedirs(cfg, exist_ok=True)
    url = _existing(cfg)
    if url:
        _say("Программа уже запущена, открываю окно: " + url.split("#")[0])
        if open_browser:
            webbrowser.open(url)
        return 0
    app = app or App(cfg_dir=cfg)
    server = make_server(app, port)
    serve_in_thread(server)
    real_port = server.server_address[1]
    url = f"http://127.0.0.1:{real_port}/#k={app.key}"
    with open(_info_path(cfg), "w", encoding="utf-8") as f:
        json.dump({"port": real_port, "key": app.key}, f)
    try:
        os.chmod(_info_path(cfg), 0o600)
    except OSError:
        pass
    _say("ДискСпас запущен.")
    _say("Если браузер не открылся сам, откройте этот адрес:")
    _say("  " + url)
    _say("Чтобы выйти, просто закройте вкладку: программа выключится сама через пару минут (если ничего не качается).")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        while not app.shutdown.wait(5):
            if not app.running() and time.time() - app.last_seen > IDLE_EXIT:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if app.running():
            app.stop()
            if app.thread:
                app.thread.join(10)
        server.shutdown()
        server.server_close()
        try:
            os.remove(_info_path(cfg))
        except OSError:
            pass
    return 0
