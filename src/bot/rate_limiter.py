from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = time.time()
        calls = self._calls[user_id]
        while calls and now - calls[0] > self.window_seconds:
            calls.popleft()
        if len(calls) >= self.max_calls:
            return False
        calls.append(now)
        return True
