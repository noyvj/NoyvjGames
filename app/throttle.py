"""In-process failure throttling for guessable endpoints (login, save codes).

Counts FAILURES per key in a sliding window and refuses further attempts once
a key has too many, until the window passes. In-process like the feedback
limiter: it resets on a restart and is per instance, which is plenty to make
online guessing impractical at this site's scale. A success clears the key so
a real player who mistyped a few times is never locked out for long.
"""

import threading
import time
from typing import Optional


class FailureLimiter:
    MAX_KEYS = 5000  # above this many tracked keys, stale ones are swept on the next write

    def __init__(self, max_failures: int, window_seconds: float):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def blocked(self, key: str, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            return len(self._recent(key, now)) >= self.max_failures

    def record_failure(self, key: str, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            recent = self._recent(key, now)
            recent.append(now)
            self._failures[key] = recent
            if len(self._failures) > self.MAX_KEYS:
                # Keys are client-chosen (usernames, forwarded addresses), so
                # sweep out the ones whose whole window has passed rather than
                # letting a flood of distinct keys grow the dict forever.
                for stale in [k for k, ts in self._failures.items() if not ts or now - ts[-1] >= self.window_seconds]:
                    del self._failures[stale]

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
