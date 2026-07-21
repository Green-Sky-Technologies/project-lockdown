"""Per-account rate limiting (in-memory token bucket).

Caps the number of ``/classify`` calls per account so one caller can't run up
the Anthropic bill (paired with a spend cap set in the Anthropic Console — the
dollar backstop; this is the call backstop). MVP is process-local; a
multi-instance deployment needs a shared store (Redis / Neon) — see A5.
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, per_minute: int, burst: int) -> None:
        self._rate = per_minute / 60.0  # tokens per second
        self._capacity = float(max(1, burst))
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Consume one token for ``key``. Returns False if the bucket is empty."""
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * self._rate)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True
