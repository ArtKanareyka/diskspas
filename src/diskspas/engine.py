"""Download engine: chunked resumable transfers, fail-fast deferral, adaptive concurrency.

Why it looks like this: during Yandex storage incidents many storage hosts accept a connection but return
0 bytes (or HTTP 500 / stall), while others work. So we (1) never block a worker on a sick file - it is
deferred and retried in later rounds, (2) fetch in small ranged chunks with a fresh link each time,
(3) tune parallelism live, and (4) persist what failed so restarts are cheap.
"""
import collections
import hashlib
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .api import AuthError
from .paths import local_path
from .priority import tier
from .tuner import Tuner


class EmptyResponse(Exception):
    """Storage host accepted the request but returned no data."""


def is_congestion(err):
    """Errors that signal overload (as opposed to a per-file problem)."""
    if isinstance(err, urllib.error.HTTPError):
        return err.code in (429, 502, 503, 504)
    text = str(err).lower()
    return any(k in text for k in ("timed out", "reset", "remotedisconnected", "connection aborted", "eof occurred"))


class Engine:
    def __init__(self, api, dest, *, prefix="disk:", start_threads=16, min_threads=4, max_threads=64,
                 chunk=8 << 20, chunk_tries=3, io_timeout=12.0, max_rounds=200, round_delay=120.0,
                 tune_interval=15.0, verify=True, state=None, sleep=time.sleep):
        self.api, self.dest, self.prefix = api, dest, prefix
        self.chunk, self.chunk_tries, self.io_timeout = chunk, chunk_tries, io_timeout
        self.max_rounds, self.round_delay, self.tune_interval = max_rounds, round_delay, tune_interval
        self.verify, self.state, self._sleep = verify, state, sleep
        self.max_threads = max_threads
        self.tuner = Tuner(start_threads, min_threads, max_threads)
        self.limit = self.tuner.limit

        self.lock = threading.Lock()
        self.cond = threading.Condition()
        self.stop = threading.Event()
        self.pause_ev = threading.Event()   # set = running, clear = paused
        self.pause_ev.set()
        self.running = 0

        self.t0 = time.time()
        self.phase = "starting"
        self.round = 0
        self.total_files = self.total_size = 0
        self.stats = {"ok": 0, "skip": 0, "failed": 0, "bytes_run": 0, "completed_bytes": 0,
                      "errors_total": 0, "attempts": 0, "cong": 0}
        self.active = {}
        self.recent = collections.deque(maxlen=15)
        self.errors = collections.deque(maxlen=15)
        self.deferred = {}        # path -> size, currently waiting for a later round
        self.deftime = {}         # path -> time of last failed attempt (persisted)
        self.failed = {}          # path -> reason (permanent)
        self.samples = collections.deque(maxlen=130)
        self.tune_note = ""
        self.listed = 0

    # ---- bookkeeping -------------------------------------------------
    def log_err(self, msg):
        with self.lock:
            self.stats["errors_total"] += 1
            self.errors.appendleft({"t": time.strftime("%H:%M:%S"), "msg": str(msg)[:200]})

    def _acquire(self):
        with self.cond:
            while (self.running >= self.limit or not self.pause_ev.is_set()) and not self.stop.is_set():
                self.cond.wait(1.0)
            self.running += 1

    def _release(self):
        with self.cond:
            self.running -= 1
            self.cond.notify()

    # ---- one chunk ---------------------------------------------------
    def _fetch_chunk(self, path, start, end, rec):
        with self.lock:
            self.stats["attempts"] += 1
        href = self.api.download_href(path)
        req = urllib.request.Request(href, headers={"Range": f"bytes={start}-{end}"})
        buf = bytearray()
        try:
            with urllib.request.urlopen(req, timeout=self.io_timeout) as resp:
                if resp.status != 206 and start:
                    raise RuntimeError(f"сервер не поддержал докачку (http {resp.status})")
                while True:
                    b = resp.read(1 << 18)
                    if not b:
                        break
                    buf += b
                    with self.lock:
                        rec["done"] += len(b)
            if not buf:
                raise EmptyResponse("сервер хранения Яндекса не отдал данные (0 байт)")
            if len(buf) != end - start + 1:
                raise RuntimeError(f"обрыв передачи: получено {len(buf)} из {end - start + 1} байт")
            with self.lock:                      # counted only once the whole piece is valid: speed never goes negative
                self.stats["bytes_run"] += len(buf)
            return buf
        except BaseException:
            with self.lock:
                rec["done"] -= len(buf)
            raise

    # ---- one file ----------------------------------------------------
    def _download(self, item):
        path = item["path"]
        rel = path[len(self.prefix):].lstrip("/") if path.startswith(self.prefix) else item["name"]
        out = local_path(self.dest, rel)
        size = int(item.get("size") or 0)
        if os.path.exists(out) and os.path.getsize(out) == size:
            return "skip"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if size == 0:
            open(out, "wb").close()
            return "ok"
        part = out + ".part"
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > size:
            os.remove(part)
            have = 0
        md5 = hashlib.md5() if (self.verify and item.get("md5")) else None
        if md5 and have:                       # resuming: hash what is already on disk once
            with open(part, "rb") as f:
                for blk in iter(lambda: f.read(1 << 20), b""):
                    md5.update(blk)
        rec = {"path": path, "size": size, "done": have, "since": time.time(), "tries": 0}
        with self.lock:
            self.active[path] = rec
        try:
            while have < size:
                while not self.pause_ev.is_set() and not self.stop.is_set():
                    self.pause_ev.wait(0.5)
                if self.stop.is_set():
                    return "defer"
                end = min(have + self.chunk, size) - 1
                data = None
                for attempt in range(self.chunk_tries):
                    try:
                        data = self._fetch_chunk(path, have, end, rec)
                        break
                    except EmptyResponse:
                        return "defer"         # sick host: retrying right now will not help
                    except AuthError:
                        raise
                    except urllib.error.HTTPError as e:
                        if e.code in (401, 403, 404):
                            self.failed[path] = f"http {e.code}"
                            return "fail"
                        err = e
                    except Exception as e:
                        err = e
                    rec["tries"] += 1
                    if is_congestion(err):
                        with self.lock:
                            self.stats["cong"] += 1
                    self.log_err(f"{os.path.basename(out)} @{have >> 20}MB: {err}")
                    self._sleep(1 + attempt)
                if data is None:
                    return "defer"
                with open(part, "ab") as f:
                    f.seek(have)
                    f.truncate()
                    f.write(data)
                if md5:
                    md5.update(data)
                have += len(data)
            if md5 and md5.hexdigest() != item["md5"]:
                os.remove(part)
                self.log_err(f"{os.path.basename(out)}: контрольная сумма не совпала, скачаю заново")
                return "defer"
            os.replace(part, out)
            return "ok"
        finally:
            with self.lock:
                self.active.pop(path, None)

    def _work(self, item, round_no):
        path, t = item["path"], time.time()
        if self.stop.is_set():
            return "defer"
        self._acquire()
        try:
            res = self._download(item)
        except AuthError:
            self.stop.set()
            self.log_err("токен отклонён, загрузка остановлена")
            res = "defer"
        except Exception as e:                 # one bad file must never kill the run
            self.log_err(f"{os.path.basename(path)}: {type(e).__name__}: {e}")
            res = "defer"
        finally:
            self._release()
        with self.lock:
            if res in ("ok", "skip"):
                self.stats[res] += 1
                self.stats["completed_bytes"] += int(item.get("size") or 0)
                self.deferred.pop(path, None)
                self.deftime.pop(path, None)
                if res == "ok":
                    self.recent.appendleft({"t": time.strftime("%H:%M:%S"), "path": path,
                                            "size": item.get("size", 0), "secs": time.time() - t})
            elif res == "defer":
                self.deferred[path] = int(item.get("size") or 0)
                self.deftime[path] = time.time()
            else:
                self.stats["failed"] += 1
        return res

    # ---- background loops ---------------------------------------------
    def _tune_loop(self):
        prev = {"t": time.time(), "b": 0, "f": 0, "a": 0, "c": 0}
        while not self.stop.wait(self.tune_interval):
            now = time.time()
            with self.lock:
                b, f = self.stats["bytes_run"], self.stats["ok"]
                a, c = self.stats["attempts"], self.stats["cong"]
            dt = max(now - prev["t"], 1e-3)
            score = ((b - prev["b"]) + 30000 * (f - prev["f"])) / dt
            att = a - prev["a"]
            crate = (c - prev["c"]) / att if att >= 10 else 0.0
            prev = {"t": now, "b": b, "f": f, "a": a, "c": c}
            old = self.limit
            new, note = self.tuner.step(score, crate)
            with self.cond:
                self.limit = new
                self.cond.notify_all()
            self.tune_note = f"{time.strftime('%H:%M:%S')} {note}; cong {crate:.0%}; limit {old}->{new}"

    def _sample_loop(self):
        while not self.stop.wait(1.0):
            self.samples.append((time.time(), self.stats["bytes_run"]))

    def _save_loop(self):
        while not self.stop.wait(20.0):
            self.save_state()

    def save_state(self):
        if self.state:
            with self.lock:
                d = dict(self.deftime)
                extra = {"ok": self.stats["ok"], "skip": self.stats["skip"]}
            self.state.save(d, **extra)

    # ---- public --------------------------------------------------------
    def pause(self):
        self.pause_ev.clear()

    def resume(self):
        self.pause_ev.set()
        with self.cond:
            self.cond.notify_all()

    def request_stop(self):
        self.stop.set()
        self.pause_ev.set()
        with self.cond:
            self.cond.notify_all()

    def snapshot(self):
        now = time.time()
        with self.lock:
            active = sorted(self.active.values(), key=lambda r: r["since"])
            act_done = sum(r["done"] for r in active)
            s = dict(self.stats)
            act = [{"path": r["path"], "size": r["size"], "done": r["done"], "age": now - r["since"],
                    "tries": r["tries"]} for r in active]
            errs, recent = list(self.errors), list(self.recent)
            deferred = [{"path": p, "size": z} for p, z in list(self.deferred.items())[:30]]
            failed = [{"path": p, "why": w} for p, w in list(self.failed.items())[:30]]
            n_def = len(self.deferred)
        smp = list(self.samples)

        def speed(win):
            if len(smp) < 2:
                return 0.0
            t1, b1 = smp[-1]
            base = [x for x in smp if t1 - x[0] <= win]
            return (b1 - base[0][1]) / max(t1 - base[0][0], 1)

        done_total = s["completed_bytes"] + act_done
        sp60 = speed(60)
        remaining = max(self.total_size - done_total, 0)
        s.update(paused=not self.pause_ev.is_set(), phase=self.phase, round=self.round, listed=self.listed, total_files=self.total_files,
                 total_size=self.total_size, limit=self.limit, max_threads=self.max_threads,
                 note=self.tune_note, active=act, errors=errs, recent=recent, deferred=deferred,
                 deferred_count=n_def, failed_list=failed, done_total=done_total, remaining=remaining,
                 speed10=speed(10), speed60=sp60, avg=s["bytes_run"] / max(now - self.t0, 1),
                 eta=(remaining / sp60) if sp60 > 1000 else None, elapsed=now - self.t0)
        s["queued"] = max(self.total_files - s["ok"] - s["skip"] - s["failed"] - len(act) - n_def, 0)
        return s

    def order(self, items):
        """Fresh files first (photos/video/docs, small before big), previously failed files last."""
        known = set(self.deftime)
        return sorted(items, key=lambda i: (i["path"] in known, tier(i["path"], int(i.get("size") or 0)),
                                            int(i.get("size") or 0)))

    def run(self, items):
        if self.state:
            now = time.time()
            self.deftime.update(self.state.load_deferred())
            self.deftime = {k: v for k, v in self.deftime.items() if now - v < 24 * 3600}
        self.total_files = len(items)
        self.total_size = sum(int(i.get("size") or 0) for i in items)
        pending = self.order(items)
        self.phase = "downloading"
        for fn in (self._tune_loop, self._sample_loop, self._save_loop):
            threading.Thread(target=fn, daemon=True).start()
        try:
            with ThreadPoolExecutor(self.max_threads) as pool:
                for rnd in range(1, self.max_rounds + 1):
                    self.round = rnd
                    results = list(pool.map(lambda it: self._work(it, rnd), pending))
                    pending = [it for it, r in zip(pending, results) if r == "defer"]
                    if not pending or self.stop.is_set():
                        break
                    self.stop.wait(self.round_delay)
        except KeyboardInterrupt:
            self.stop.set()
            self.phase = "interrupted"
            raise
        finally:
            self.save_state()
        self.phase = "done" if not pending else ("stopped" if self.stop.is_set() else "done (unfinished files)")
        report = self.report(pending)
        if self.state:
            self.state.write_report(report)
        self.stop.set()
        return pending

    def report(self, unfinished):
        s = self.stats
        lines = [f"Всего файлов: {self.total_files}", f"Скачано сейчас: {s['ok']}", f"Уже были скачаны: {s['skip']}",
                 f"Не скачались совсем: {s['failed']}", f"Ждут (сервер Яндекса их пока не отдаёт): {len(unfinished)}", ""]
        lines += [f"ОШИБКА {p}: {w}" for p, w in self.failed.items()]
        lines += [f"НЕ СКАЧАНО {it['path']}" for it in unfinished]
        return "\n".join(lines) + "\n"
