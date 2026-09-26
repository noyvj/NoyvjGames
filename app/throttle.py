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

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
