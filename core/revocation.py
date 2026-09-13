"""In-memory JWT denylist keyed by ``jti`` with expiry parity.

Revoked token ids are kept only until the token's own ``exp`` — after that the
JWT signature/expiry check rejects it anyway, so entries are dropped lazily on
lookup and eagerly on each new revocation.

Single-process by design, with two consequences (see docs/EVALUATION.md
limitation 6): limits are per-worker under multi-worker deployments, and a
process restart clears the denylist, so tokens revoked before a restart become
valid again until expiry. A shared store (e.g. Redis) is the upgrade path.
"""

import threading
import time
from collections.abc import Callable


class TokenDenylist:
    """Tracks revoked JWT ``jti`` values until their tokens expire."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._revoked: dict[str, float] = {}
        self._clock = clock or time.time
        self._lock = threading.Lock()

    def revoke(self, jti: str, exp: float) -> None:
        """Revoke ``jti``; the entry is dropped once ``exp`` has passed."""
        with self._lock:
            self._purge()
            self._revoked[jti] = exp

    def is_revoked(self, jti: str) -> bool:
        """Return True while ``jti`` is revoked and its token has not expired."""
        with self._lock:
            exp = self._revoked.get(jti)
            if exp is None:
                return False
            if exp <= self._clock():
                del self._revoked[jti]
                return False
            return True

    def reset_all(self) -> None:
        """Clear every entry; used by tests and administrative resets."""
        with self._lock:
            self._revoked.clear()

    def _purge(self) -> None:
        now = self._clock()
        expired = [jti for jti, exp in self._revoked.items() if exp <= now]
        for jti in expired:
            del self._revoked[jti]


token_denylist = TokenDenylist()
