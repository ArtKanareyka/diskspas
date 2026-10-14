import unittest

import _path  # noqa: F401
from diskspas.paths import local_path, safe_part
from diskspas.priority import tier
from diskspas.tuner import Tuner


class PathTests(unittest.TestCase):
    def test_trailing_space_and_dot(self):
        self.assertEqual(safe_part("Темины родители "), "Темины родители_")
        self.assertEqual(safe_part("name."), "name_")

    def test_forbidden_characters(self):
        self.assertEqual(safe_part('a:b?c*d"e|f<g>h'), "a_b_c_d_e_f_g_h")

    def test_reserved_and_empty(self):
        self.assertEqual(safe_part("CON"), "_CON")
        self.assertEqual(safe_part("nul.txt"), "_nul.txt")
        self.assertEqual(safe_part(".."), "_")
        self.assertEqual(safe_part(""), "_")

    def test_normal_names_untouched(self):
        self.assertEqual(safe_part("Фото 2024 (1).jpg"), "Фото 2024 (1).jpg")

    def test_local_path_stays_under_dest(self):
        p = local_path("C:\\x\\dest" if __import__("os").name == "nt" else "/tmp/dest", "../../etc/passwd")
        self.assertIn("dest", p)
        self.assertNotIn("..", p.replace("\\\\?\\", ""))


class PriorityTests(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(tier("disk:/Photos/a.jpg", 2_000_000), 0)
        self.assertEqual(tier("disk:/Photos/tiny.jpg", 100), 1)
        self.assertEqual(tier("disk:/x/data.bin", 5_000_000), 1)
        self.assertEqual(tier("disk:/Backup/AppData/Local/cache.bin", 5_000_000), 2)
        self.assertEqual(tier("disk:/Games/minecraft/world/level.dat", 5_000_000), 1)   # game saves are real data
        self.assertEqual(tier("disk:/a/~$report.docx", 162), 2)
        self.assertEqual(tier("disk:/a/Desktop.ini", 100), 2)


class TunerTests(unittest.TestCase):
    @staticmethod
    def throughput(limit):
        # rises linearly, saturates at 24 workers
        return min(limit, 24) * 1.0e6

    def run_tuner(self, windows=60, **kw):
        t = Tuner(**kw)
        for _ in range(windows):
            t.step(self.throughput(t.limit), 0.0)
        return t

    def test_converges_to_saturation_without_running_away(self):
        t = self.run_tuner(start=4, lo=2, hi=64)
        self.assertGreaterEqual(t.limit, 20)
        self.assertLessEqual(t.limit, 36)

    def test_backs_off_on_congestion(self):
        t = Tuner(start=40, lo=4, hi=64)
        limit, note = t.step(1e6, 0.6)
        self.assertEqual(limit, 28)
        self.assertIn("congestion", note)

    def test_respects_bounds(self):
        t = Tuner(start=4, lo=4, hi=8)
        for _ in range(30):
            t.step(1e9 * t.limit, 0.0)
        self.assertLessEqual(t.limit, 8)
        t2 = Tuner(start=5, lo=4, hi=8)
        for _ in range(10):
            t2.step(1.0, 0.9)
        self.assertGreaterEqual(t2.limit, 4)


if __name__ == "__main__":
    unittest.main()
