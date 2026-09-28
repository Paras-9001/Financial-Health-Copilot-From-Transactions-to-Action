"""Bounded, single-process limiter for the Phase 0 local demo."""

from collections import deque
from threading import Lock
from time import monotonic

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import APIError


class AuthRateLimiter:
    def __init__(self):
        self.entries: dict[str, deque[float]] = {}
        self.lock = Lock()

    def check(self, key: str):
        settings = get_settings()
        now = monotonic()
        cutoff = now - settings.auth_rate_window_seconds
        with self.lock:
            for address in list(self.entries):
                queue = self.entries[address]
                while queue and queue[0] <= cutoff:
                    queue.popleft()
                if not queue:
                    del self.entries[address]
            if key not in self.entries:
                if len(self.entries) >= settings.auth_rate_max_clients:
                    raise APIError(429, "rate_limited", "Please wait before trying again.")
                self.entries[key] = deque()
            queue = self.entries[key]
            if len(queue) >= settings.auth_rate_limit:
                raise APIError(
                    429,
                    "rate_limited",
                    "Too many attempts. Try again shortly.",
                    headers={"Retry-After": str(settings.auth_rate_window_seconds)},
                )
            queue.append(now)


limiter = AuthRateLimiter()


def limit_auth(request: Request):
    # Do not trust arbitrary X-Forwarded-For supplied by a client.
    limiter.check(request.client.host if request.client else "unknown")
