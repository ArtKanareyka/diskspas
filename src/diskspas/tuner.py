"""Adaptive concurrency: hill climbing with multiplicative back-off (AIMD-like)."""


class Tuner:
    """Decides how many downloads to run in parallel.

    Call step(score, congestion_rate) once per window. `score` is useful work per second (bytes plus a
    per-file bonus, so tiny-file phases register too); `congestion_rate` is the share of requests that
    failed in a way that signals overload (timeouts, resets, 429/502/503/504).
    """

    def __init__(self, start=16, lo=4, hi=64, gain=1.03, congestion=0.25):
        self.limit = max(lo, min(hi, start))
        self.lo, self.hi = lo, hi
        self.gain = gain
        self.congestion = congestion
        self.prev_limit = self.limit
        self.last_score = 0.0
        self.probing = False
        self.hold = 0

    def step(self, score, crate):
        lim = self.limit
        if crate > self.congestion:
            self.limit = max(self.lo, int(lim * 0.7))
            self.hold, self.probing = 2, False
            note = f"congestion {crate:.0%}: back off"
        elif self.hold > 0:
            self.hold -= 1
            note = "holding"
        elif self.probing and score <= self.last_score * self.gain:
            self.limit = self.prev_limit
            self.hold, self.probing = 4, False
            note = "no gain: revert, plateau"
        else:
            self.prev_limit = lim
            self.limit = min(self.hi, lim + max(2, lim // 5))
            self.probing = self.limit != lim
            note = "probing higher" if self.probing else "at max"
        self.last_score = score
        return self.limit, note
