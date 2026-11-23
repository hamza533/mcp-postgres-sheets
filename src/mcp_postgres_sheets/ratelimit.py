"""Per-caller sliding-window rate limit (remote mode): at most N tool calls per 60 s per caller.

State is per process. With several replicas each enforces the limit on its own share of
traffic, which keeps the server stateless; put a gateway limit in front for a global cap
(see docs/DECISIONS.md).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable

WINDOW_S = 60.0
MAX_TRACKED_CALLERS = 10_000


class RateLimiter:
    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.per_minute = per_minute
        self._clock = clock
        self._calls: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            window = self._calls.get(key)
            if window is None:
                window = deque()
                self._calls[key] = window
            self._calls.move_to_end(key)
            while window and now - window[0] >= WINDOW_S:
                window.popleft()
            if len(window) >= self.per_minute:
                return False
            window.append(now)
            while len(self._calls) > MAX_TRACKED_CALLERS:
                self._calls.popitem(last=False)  # forget the least recently seen caller
            return True
