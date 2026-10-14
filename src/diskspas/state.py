"""Persistent state kept inside the destination folder (resumable across restarts)."""
import json
import os
import time


class StateStore:
    def __init__(self, dest):
        self.dir = os.path.join(dest, ".diskspas")
        os.makedirs(self.dir, exist_ok=True)
        self.state_file = os.path.join(self.dir, "state.json")
        self.listing_file = os.path.join(self.dir, "listing.json")
        self.report_file = os.path.join(self.dir, "report.txt")

    def _write(self, path, data):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)

    def load_deferred(self, max_age=24 * 3600):
        try:
            with open(self.state_file, encoding="utf-8") as f:
                d = json.load(f).get("deferred", {})
        except Exception:
            return {}
        now = time.time()
        return {k: v for k, v in d.items() if now - v < max_age}

    def save(self, deferred, **extra):
        self._write(self.state_file, {"saved": time.time(), "deferred": deferred, **extra})

    def load_listing(self, key, max_age=6 * 3600):
        try:
            if time.time() - os.path.getmtime(self.listing_file) > max_age:
                return None
            with open(self.listing_file, encoding="utf-8") as f:
                d = json.load(f)
            return d["items"] if d.get("key") == key else None
        except Exception:
            return None

    def save_listing(self, key, items):
        self._write(self.listing_file, {"key": key, "items": items})

    def write_report(self, text):
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(text)
