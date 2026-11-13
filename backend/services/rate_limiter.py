"""Lightweight in-memory token bucket rate limiter for auth and SOS endpoints."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Callable
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Rate limits: (max_requests, window_seconds)
RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/auth/login": (10, 60),               # 10 login attempts per minute per IP
    "/auth/register": (10, 60),            # 10 registrations per minute per IP
    "/auth/register/provider": (10, 60),   # 10 provider registrations per minute per IP
    "/sos": (30, 60),                      # 30 SOS submissions per minute per IP
}


class TokenBucketLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        # client_ip:endpoint -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_prune = time.time()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "127.0.0.1"

    def is_rate_limited(self, request: Request) -> tuple[bool, int]:
        """Check if request exceeds rate limits. Returns (is_limited, retry_after_seconds)."""
        # Allow disabling in unit tests or when explicitly bypassed
        if os.getenv("TESTING", "0") == "1" or os.getenv("RATE_LIMIT_ENABLED", "1") == "0":
            return False, 0

        path = request.url.path.rstrip("/")
        # Only check POST requests on registered sensitive paths
        if request.method != "POST":
            return False, 0

        rule = RATE_LIMIT_RULES.get(path)
        if not rule:
            return False, 0

        max_requests, window_seconds = rule
        client_ip = self._get_client_ip(request)
        key = f"{client_ip}:{path}"
        now = time.time()

        with self._lock:
            # Periodic cleanup every 5 minutes
            if now - self._last_prune > 300:
                self._prune_expired(now)

            timestamps = self._requests[key]
            # Discard timestamps outside the window
            cutoff = now - window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._requests[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - earliest)))
                return True, retry_after

            self._requests[key].append(now)
            return False, 0

    def _prune_expired(self, now: float) -> None:
        """Remove empty or fully expired IP buckets."""
        max_window = max(w for _, w in RATE_LIMIT_RULES.values())
        cutoff = now - max_window
        stale_keys = [
            k for k, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] < cutoff
        ]
        for k in stale_keys:
            del self._requests[k]
        self._last_prune = now


_limiter = TokenBucketLimiter()


def get_limiter() -> TokenBucketLimiter:
    return _limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware applying rate limits to sensitive routes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        is_limited, retry_after = _limiter.is_rate_limited(request)
        if is_limited:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait before retrying.",
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
