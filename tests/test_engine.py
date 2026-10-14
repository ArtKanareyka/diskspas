import hashlib
import os
import random
import shutil
import tempfile
import unittest

import _path  # noqa: F401
from fake_yandex import FakeYandex
from diskspas.api import Api, AuthError
from diskspas.engine import Engine
from diskspas.paths import local_path
from diskspas.state import StateStore


def blob(n, seed):
    return random.Random(seed).randbytes(n)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="yrescue_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.servers = []

    def tearDown(self):
        for s in self.servers:
            s.close()

    def make(self, files, plan=None, **engine_kw):
        srv = FakeYandex(files, plan, stall_seconds=1.5)
        self.servers.append(srv)
        api = Api("T0KEN", base=srv.base, timeout=5, sleep=lambda s: None)
        kw = dict(start_threads=4, min_threads=2, max_threads=8, chunk=1000, io_timeout=0.5,
                  round_delay=0.05, tune_interval=0.2, sleep=lambda s: None, max_rounds=6)
        kw.update(engine_kw)
        eng = Engine(api, self.tmp, state=StateStore(self.tmp), **kw)
        return srv, api, eng

    def read(self, disk_path):
        rel = disk_path[len("disk:"):].lstrip("/")
        with open(local_path(self.tmp, rel), "rb") as f:
            return f.read()

    def test_downloads_everything_identically(self):
        files = {
            "disk:/Фото/one.jpg": blob(2500, 1),                 # multi-chunk
            "disk:/Фото/empty.txt": b"",                         # zero byte
            "disk:/a dir /trailing space.bin": blob(999, 2),    # trailing space in folder name
            "disk:/weird/a:b?.txt": blob(10, 3),                 # forbidden characters
            "disk:/big.bin": blob(12345, 4),
        }
        srv, api, eng = self.make(files)
        unfinished = eng.run(api.list_files())
        self.assertEqual(unfinished, [])
        for p, data in files.items():
            self.assertEqual(self.read(p), data, p)
        self.assertEqual(eng.stats["failed"], 0)

    def test_recovers_from_sick_storage_hosts(self):
        files = {f"disk:/f{i}.bin": blob(1500, i) for i in range(6)}
        plan = {"disk:/f1.bin": ["empty", "empty"],       # sick host, then healthy
                "disk:/f2.bin": ["500", "500", "500", "500"],
                "disk:/f3.bin": ["stall"]}                 # slower than the io timeout
        srv, api, eng = self.make(files, plan)
        unfinished = eng.run(api.list_files())
        self.assertEqual(unfinished, [])
        for p, data in files.items():
            self.assertEqual(self.read(p), data, p)
        self.assertGreater(eng.stats["errors_total"], 0)

    def test_permanently_sick_file_does_not_block_others_and_is_reported(self):
        files = {"disk:/ok1.bin": blob(1200, 1), "disk:/dead.bin": blob(1200, 2), "disk:/ok2.bin": blob(1200, 3)}
        srv, api, eng = self.make(files, {"disk:/dead.bin": ["empty"] * 1000}, max_rounds=3)
        unfinished = eng.run(api.list_files())
        self.assertEqual([i["path"] for i in unfinished], ["disk:/dead.bin"])
        self.assertEqual(self.read("disk:/ok1.bin"), files["disk:/ok1.bin"])
        self.assertEqual(self.read("disk:/ok2.bin"), files["disk:/ok2.bin"])
        with open(StateStore(self.tmp).report_file, encoding="utf-8") as f:
            report = f.read()
        self.assertIn("НЕ СКАЧАНО disk:/dead.bin", report)

    def test_resumes_from_part_file_without_refetching(self):
        data = blob(5000, 7)
        files = {"disk:/resume.bin": data}
        srv, api, eng = self.make(files)
        out = local_path(self.tmp, "resume.bin")
        with open(out + ".part", "wb") as f:
            f.write(data[:3000])
        eng.run(api.list_files())
        self.assertEqual(self.read("disk:/resume.bin"), data)
        self.assertEqual(srv.bytes_served, 2000)               # only the missing tail

    def test_skips_files_already_present(self):
        data = blob(3000, 9)
        files = {"disk:/have.bin": data}
        srv, api, eng = self.make(files)
        out = local_path(self.tmp, "have.bin")
        with open(out, "wb") as f:
            f.write(data)
        eng.run(api.list_files())
        self.assertEqual(srv.requests.get("disk:/have.bin", 0), 0)
        self.assertEqual(eng.stats["skip"], 1)

    def test_md5_mismatch_is_redone(self):
        data = blob(2000, 11)
        srv, api, eng = self.make({"disk:/c.bin": data}, {"disk:/c.bin": ["corrupt", "corrupt"]})
        unfinished = eng.run(api.list_files())
        self.assertEqual(unfinished, [])
        self.assertEqual(hashlib.md5(self.read("disk:/c.bin")).hexdigest(), hashlib.md5(data).hexdigest())

    def test_bad_token_stops_cleanly(self):
        srv = FakeYandex({"disk:/a.bin": b"x" * 10})
        self.servers.append(srv)
        api = Api("WRONG", base=srv.base, timeout=5, sleep=lambda s: None)
        with self.assertRaises(AuthError):
            api.list_files()

    def test_state_is_persisted_and_failed_files_go_last(self):
        files = {"disk:/a.bin": blob(1100, 1), "disk:/b.bin": blob(1100, 2)}
        srv, api, eng = self.make(files, {"disk:/a.bin": ["empty"] * 1000}, max_rounds=1)
        eng.run(api.list_files())
        self.assertIn("disk:/a.bin", StateStore(self.tmp).load_deferred())
        eng2 = Engine(api, self.tmp, state=StateStore(self.tmp))
        eng2.deftime.update(StateStore(self.tmp).load_deferred())
        order = [i["path"] for i in eng2.order(api.list_files())]
        self.assertEqual(order[-1], "disk:/a.bin")


if __name__ == "__main__":
    unittest.main()
