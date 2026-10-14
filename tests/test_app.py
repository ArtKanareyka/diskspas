import http.client
import json
import os
import random
import shutil
import tempfile
import time
import unittest
import urllib.parse

import _path  # noqa: F401
from fake_yandex import FakeYandex
from diskspas.app import App
from diskspas.paths import local_path
from diskspas.web import make_server, serve_in_thread

ENGINE_KW = dict(chunk=1000, io_timeout=1.0, round_delay=0.05, tune_interval=0.2,
                 sleep=lambda s: None, max_rounds=5)


def blob(n, seed):
    return random.Random(seed).randbytes(n)


class UiBase(unittest.TestCase):
    delay = 0.0

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="yui_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cfg = os.path.join(self.tmp, "cfg")
        self.dest = os.path.join(self.tmp, "dest")
        self.files = {
            "disk:/Photos/a.jpg": blob(2500, 1), "disk:/Photos/2024/b.jpg": blob(1800, 2),
            "disk:/Docs/report.pdf": blob(3100, 3), "disk:/root.txt": blob(50, 4),
            "disk:/Backup/AppData/Local/cache.bin": blob(900, 5),
        }
        self.fake = FakeYandex(self.files, delay=self.delay)
        self.app = App(api_base=self.fake.base, cfg_dir=self.cfg, engine_kw=ENGINE_KW)
        self.server = make_server(self.app, 0)
        serve_in_thread(self.server)
        self.port = self.server.server_address[1]
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if self.app.running():
            self.app.stop()
            self.app.thread.join(5)
        self.server.shutdown()
        self.server.server_close()
        self.fake.close()

    def call(self, method, path, body=None, key="ok", host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if key == "ok":
            headers["X-Key"] = self.app.key
        elif key:
            headers["X-Key"] = key
        data = json.dumps(body).encode() if body is not None else None
        if data:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, raw

    def status(self):
        return self.call("GET", "/api/status")[1]

    def login(self):
        code, d = self.call("POST", "/api/login", {"token": "T0KEN"})
        self.assertEqual(code, 200, d)

    def wait(self, cond, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.05)
        return False

    def scan(self, selection=(), skip_junk=False):
        code, d = self.call("POST", "/api/scan", {"selection": list(selection), "skip_junk": skip_junk})
        self.assertEqual(code, 200, d)
        self.assertTrue(self.wait(lambda: self.status()["scan"]["state"] in ("done", "error")))
        return self.status()

    def start(self, **opts):
        code, d = self.call("POST", "/api/start", {"dest": self.dest, "options": {"max_threads": 8, **opts}})
        self.assertEqual(code, 200, d)

    def run_job(self, **opts):
        self.start(**opts)
        self.assertTrue(self.wait(lambda: not self.status()["running"], 30))
        return self.status()

    def read(self, disk_path):
        with open(local_path(self.dest, disk_path[len("disk:"):].lstrip("/")), "rb") as f:
            return f.read()


class UiTests(UiBase):
    # ---------------------------------------------------------------- security
    def test_api_requires_key_and_valid_host(self):
        self.assertEqual(self.call("GET", "/api/status", key=None)[0], 403)
        self.assertEqual(self.call("GET", "/api/status", key="wrong")[0], 403)
        self.assertEqual(self.call("POST", "/api/pause", {}, key=None)[0], 403)
        self.assertFalse(self.app.shutdown.is_set())
        self.assertEqual(self.call("GET", "/api/status", host="evil.example.com")[0], 403)   # DNS rebinding
        self.assertEqual(self.call("GET", "/api/status")[0], 200)

    def test_page_is_served_without_key_but_only_on_local_host(self):
        code, body = self.call("GET", "/", key=None)
        self.assertEqual(code, 200)
        self.assertIn("ДискСпас".encode("utf-8"), body)
        self.assertEqual(self.call("GET", "/", key=None, host="evil.example.com")[0], 403)

    # ------------------------------------------------------------------- login
    def test_login_flow_and_token_persistence(self):
        self.assertFalse(self.status()["logged_in"])
        code, d = self.call("POST", "/api/login", {"token": "nope"})
        self.assertEqual((code, d["code"]), (400, "bad_token"))
        self.assertEqual(self.call("POST", "/api/login", {"token": ""})[1]["code"], "empty_token")
        self.login()
        st = self.status()
        self.assertTrue(st["logged_in"])
        self.assertEqual(st["disk"]["total"], 10 ** 12)
        self.assertTrue(os.path.exists(os.path.join(self.cfg, "token")))
        app2 = App(api_base=self.fake.base, cfg_dir=self.cfg)       # restart: stays logged in
        self.assertIsNotNone(app2.api)
        self.call("POST", "/api/logout", {})
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "token")))

    def test_endpoints_need_login(self):
        code, d = self.call("GET", "/api/tree?path=disk:/")
        self.assertEqual((code, d["code"]), (400, "not_logged_in"))

    # ---------------------------------------------------------------- browsing
    def test_disk_tree_lists_folders_first(self):
        self.login()
        code, items = self.call("GET", "/api/tree?path=" + urllib.parse.quote("disk:/"))
        self.assertEqual(code, 200)
        self.assertEqual([i["name"] for i in items], ["Backup", "Docs", "Photos", "root.txt"])
        self.assertEqual(items[0]["type"], "dir")
        self.assertEqual(items[-1]["size"], 50)

    def test_local_folder_browser_and_mkdir(self):
        os.makedirs(os.path.join(self.tmp, "one"))
        code, d = self.call("GET", "/api/fs?path=" + urllib.parse.quote(self.tmp))
        self.assertEqual(code, 200)
        self.assertIn("one", d["dirs"])
        self.assertIsNotNone(d["free"])
        code, d = self.call("POST", "/api/mkdir", {"parent": self.tmp, "name": "Мои копии"})
        self.assertEqual(code, 200)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "Мои копии")))
        for bad in ("../x", "a/b", "a:b", "", ".."):
            self.assertEqual(self.call("POST", "/api/mkdir", {"parent": self.tmp, "name": bad})[0], 400, bad)
        code, d = self.call("GET", "/api/fs?path=")                  # roots listing
        self.assertEqual(code, 200)
        self.assertTrue(d["roots"])

    # ----------------------------------------------------------- full download
    def test_whole_disk_download_through_the_ui_api(self):
        self.login()
        st = self.scan()
        self.assertEqual(st["plan"]["files"], len(self.files))
        st = self.run_job()
        self.assertEqual(st["job"]["failed"], 0)
        self.assertEqual(st["job"]["phase"], "done")
        for p, data in self.files.items():
            self.assertEqual(self.read(p), data, p)
        self.assertEqual(self.status()["dest"], self.dest)
        self.assertEqual(self.call("POST", "/api/reset", {})[0], 200)

    def test_only_selected_folders_and_files(self):
        self.login()
        st = self.scan(["disk:/Photos", "disk:/root.txt"])
        self.assertEqual(st["plan"]["files"], 3)
        self.run_job()
        self.assertEqual(self.read("disk:/Photos/2024/b.jpg"), self.files["disk:/Photos/2024/b.jpg"])
        self.assertEqual(self.read("disk:/root.txt"), self.files["disk:/root.txt"])
        self.assertFalse(os.path.exists(local_path(self.dest, "Docs/report.pdf")))

    def test_skip_junk_option(self):
        self.login()
        st = self.scan(skip_junk=True)
        self.assertEqual(st["plan"]["files"], len(self.files) - 1)
        self.assertEqual(st["plan"]["junk_files"], 1)
        self.run_job()
        self.assertFalse(os.path.exists(local_path(self.dest, "Backup/AppData/Local/cache.bin")))

    def test_start_validations(self):
        self.login()
        self.assertEqual(self.call("POST", "/api/start", {"dest": self.dest})[1]["code"], "no_plan")
        self.scan()
        self.assertEqual(self.call("POST", "/api/start", {"dest": ""})[1]["code"], "no_dest")
        root = os.path.abspath(os.sep)
        self.assertEqual(self.call("POST", "/api/start", {"dest": root})[1]["code"], "root_dest")
        self.assertFalse(os.path.exists(os.path.join(os.getcwd(), ".diskspas")))   # nothing written to cwd
        self.app.plan["bytes"] = 10 ** 18
        code, d = self.call("POST", "/api/start", {"dest": self.dest})
        self.assertEqual((code, d["code"]), (400, "no_space"))


class ControlTests(UiBase):
    delay = 0.12

    def many(self, n, seed):
        self.files.update({f"disk:/many/f{i:02d}.bin": blob(1200, seed + i) for i in range(n)})
        self.fake.files = dict(self.files)
        self.login()
        self.scan(["disk:/many"])

    def test_pause_and_resume(self):
        self.many(40, 100)
        self.start(start_threads=4)
        self.assertTrue(self.wait(lambda: self.status()["job"]["ok"] >= 2))
        self.call("POST", "/api/pause", {})
        time.sleep(0.6)                                              # let in-flight files finish
        c1 = self.status()["job"]
        time.sleep(0.8)
        c2 = self.status()["job"]
        self.assertTrue(c2["paused"])
        self.assertEqual(c1["ok"], c2["ok"])                         # nothing progressed while paused
        self.assertLess(c2["ok"], 40)
        self.call("POST", "/api/resume", {})
        self.assertTrue(self.wait(lambda: not self.status()["running"], 40))
        self.assertEqual(self.status()["job"]["ok"], 40)

    def test_stop_keeps_progress_and_can_continue(self):
        self.many(30, 200)
        self.start(start_threads=4)
        self.assertTrue(self.wait(lambda: self.status()["job"]["ok"] >= 3))
        self.call("POST", "/api/stop", {})
        self.assertTrue(self.wait(lambda: not self.status()["running"], 15))
        self.assertLess(self.status()["job"]["ok"], 30)
        self.call("POST", "/api/reset", {})
        self.scan(["disk:/many"])
        job = self.run_job()["job"]
        self.assertEqual(job["ok"] + job["skip"], 30)               # earlier files were kept, not redone


if __name__ == "__main__":
    unittest.main()


class PublicLinkTest(UiBase):
    def test_public_link_download_without_token(self):
        self.assertEqual(self.call("POST", "/api/login_public", {"link": "https://example.com/x"})[0], 400)
        self.assertEqual(self.call("POST", "/api/login_public", {"link": "https://disk.yandex.ru/d/NOPE"})[0], 400)
        code, st = self.call("POST", "/api/login_public", {"link": "  " + FakeYandex.PUBLIC_LINK + " "})
        self.assertEqual(code, 200)
        self.assertTrue(st["logged_in"])
        self.assertIsNotNone(st["public"])
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "token")))      # nothing persisted
        code, kids = self.call("GET", "/api/tree?path=disk%3A%2F")
        self.assertEqual({k["name"] for k in kids}, {"Photos", "Docs", "Backup", "root.txt"})
        self.assertEqual(self.call("POST", "/api/scan", {"selection": []})[0], 200)
        for _ in range(100):
            if self.call("GET", "/api/status")[1]["scan"]["state"] == "done":
                break
            time.sleep(0.05)
        self.assertEqual(self.call("GET", "/api/status")[1]["plan"]["files"], 5)
        self.assertEqual(self.call("POST", "/api/start", {"dest": self.dest})[0], 200)
        self.app.thread.join(20)
        for p, data in self.files.items():
            with open(os.path.join(self.dest, p[len("disk:/"):]), "rb") as f:
                self.assertEqual(f.read(), data)
