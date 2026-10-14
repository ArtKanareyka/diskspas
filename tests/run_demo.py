"""Manual demo: the real UI against a fake Yandex Disk. Usage: python tests/run_demo.py [port]

Token for the demo login: T0KEN. Some files are 'sick' on purpose to show the waiting list.
"""
import os
import random
import sys
import tempfile

import _path  # noqa: F401
from fake_yandex import FakeYandex
from diskspas.app import App
from diskspas.launcher import run_ui

rnd = random.Random(7)
files = {}
for year in ("2023", "2024"):
    for place in ("Отпуск в Крыму", "Дача", "День рождения"):
        for i in range(1, 6):
            files[f"disk:/Фото/{year}/{place}/IMG_{i:04d}.jpg"] = rnd.randbytes(rnd.randint(150_000, 600_000))
for i in range(1, 5):
    files[f"disk:/Документы/Университет/Курсовая_{i}.docx"] = rnd.randbytes(rnd.randint(40_000, 90_000))
files["disk:/Видео/свадьба.mp4"] = rnd.randbytes(3_000_000)
files["disk:/Резервная копия/AppData/Local/cache.bin"] = rnd.randbytes(30_000)
files["disk:/Папка с пробелом /заметка.txt"] = b"hello"
files["disk:/Файл.txt"] = b"x" * 100

plan = {"disk:/Фото/2024/Дача/IMG_0003.jpg": ["empty"] * 4, "disk:/Видео/свадьба.mp4": ["500", "empty"]}
fake = FakeYandex(files, plan, delay=0.12)
cfg = tempfile.mkdtemp(prefix="demo_cfg_")
app = App(api_base=fake.base, cfg_dir=cfg, engine_kw=dict(round_delay=6.0, chunk=256 * 1024, tune_interval=3.0))
print("DEMO backend ready; demo token: T0KEN", flush=True)
run_ui(port=int(sys.argv[1]) if len(sys.argv) > 1 else 8777, open_browser=False, cfg_dir=cfg, app=app)
