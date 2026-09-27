"""
In-memory, per-process rate limiting middleware. No new dependency (no Redis, no slowapi) -
appropriate for a single-instance MVP deployment, but it resets on restart and doesn't coordinate
across multiple backend processes/instances. If PaperBites moves to horizontal scaling, replace
the in-memory `_hits` dict below with a shared store keyed the same way.

Two tiers, keyed by client IP:
- Sensitive auth endpoints (signup/login/forgot-password/reset-password) get a tight limit,
  since these are exactly what credential-stuffing, signup spam, and account enumeration would
  target.
- Everything else under /api gets a much looser general limit, just to stop a runaway client or
  basic scripted abuse from overwhelming the server. Non-API paths aren't limited at all.
"""
import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse

SENSITIVE_PATHS = {
    "/api/auth/login",
    "/api/auth/signup",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}
SENSITIVE_LIMIT = 10
SENSITIVE_WINDOW_SECONDS = 60

GENERAL_LIMIT = 120
GENERAL_WINDOW_SECONDS = 60

_hits = defaultdict(deque)  # bucket key -> deque of hit timestamps, oldest first


def _client_ip(scope) -> str:
    client = scope.get("client")
    return client[0] if client else "unknown"


def _check_and_record(bucket_key, limit, window_seconds) -> bool:
    now = time.time()
    hits = _hits[bucket_key]
    while hits and now - hits[0] > window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(now)
    return True


class RateLimitMiddleware:
    """Raw ASGI middleware (not BaseHTTPMiddleware) so it can short-circuit with a 429 before
    the request body is ever read, and so it composes cleanly under Starlette's CORS middleware
    without needing to await the downstream response first."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api"):
            await self.app(scope, receive, send)
            return

        ip = _client_ip(scope)
        path = scope["path"]

        if path in SENSITIVE_PATHS:
            allowed = _check_and_record(("sensitive", ip, path), SENSITIVE_LIMIT, SENSITIVE_WINDOW_SECONDS)
        else:
            allowed = _check_and_record(("general", ip), GENERAL_LIMIT, GENERAL_WINDOW_SECONDS)

        if not allowed:
            response = JSONResponse(
                {"detail": "Too many requests. Please try again in a minute."},
                status_code=429,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
