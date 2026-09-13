"""In-memory sliding-window rate limiter for login brute-force protection.

Single-process by design: counters live in this process's memory, so limits are
per-worker under multi-worker deployments (uvicorn --workers N, containers) and
reset on restart. A shared store (e.g. Redis) is the upgrade path when the app
scales beyond one process; see docs/EVALUATION.md limitation 5.
"""

import threading
import time
from collections import deque
from collections.abc import Callable
from math import ceil

from core.config import settings


class SlidingWindowLimiter:
    """Limits keys to ``max_attempts`` hits per rolling ``window_seconds``.

    Blocked attempts are not recorded, so a lockout expires
    ``window_seconds`` after the last allowed attempt and cannot be extended
    by hammering. The clock is injectable for deterministic tests.
    """

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock or _monotonic
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._hits = 0

    def hit(self, key: str) -> int | None:
        """Record one attempt for ``key``.

        Returns the Retry-After value in whole seconds when the key is already
        at the limit, or None when the attempt is allowed.
        """
        now = self._clock()
        with self._lock:
            self._hits += 1
            if self._hits % 128 == 0:
                self._sweep(now)

            stamps = self._attempts.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while stamps and stamps[0] <= cutoff:
                stamps.popleft()

            if len(stamps) >= self.max_attempts:
                return max(1, ceil(stamps[0] + self.window_seconds - now))

            stamps.append(now)
            return None

    def reset(self, key: str) -> None:
        """Clear one key's history."""
        with self._lock:
            self._attempts.pop(key, None)

    def reset_all(self) -> None:
        """Clear every key; used by tests and administrative resets."""
        with self._lock:
            self._attempts.clear()

    def _sweep(self, now: float) -> None:
        cutoff = now - self.window_seconds
        empty = [
            key for key, stamps in self._attempts.items() if not stamps or stamps[-1] <= cutoff
        ]
        for key in empty:
            del self._attempts[key]


def _monotonic() -> float:
    return time.monotonic()


login_limiter = SlidingWindowLimiter(
    max_attempts=settings.LOGIN_RATE_LIMIT_ATTEMPTS,
    window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)
