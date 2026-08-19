"""Rate limiting middleware using token bucket algorithm."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, rate: int, per: int = 60) -> None:
        self.rate = rate  # tokens per period
        self.per = per    # period in seconds
        self.tokens = rate
        self.last_update = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.monotonic()
        # Refill tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate / self.per)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket per client IP.

    Reads rate limit from settings dynamically to support runtime configuration changes.
    """

    def __init__(self, app, rate_limit_getter: Optional[Callable[[], int]] = None, per: int = 60) -> None:
        super().__init__(app)
        self._rate_limit_getter = rate_limit_getter or (lambda: get_settings().rate_limit_per_minute)
        self.per = per
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self._rate_limit_getter(), per)
        )

    def _get_rate_limit(self) -> int:
        """Get current rate limit from settings."""
        return self._rate_limit_getter()

    def _get_client_key(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if behind proxy, otherwise client host
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_or_create_bucket(self, client_key: str) -> TokenBucket:
        """Get or create bucket for client, updating rate limit if changed."""
        bucket = self.buckets[client_key]
        current_rate = self._get_rate_limit()
        if bucket.rate != current_rate:
            # Create new bucket with updated rate limit
            bucket = TokenBucket(current_rate, self.per)
            self.buckets[client_key] = bucket
        return bucket

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/api/v1/health", "/api/v1/ready"):
            return await call_next(request)

        client_key = self._get_client_key(request)
        bucket = self._get_or_create_bucket(client_key)

        if not bucket.consume():
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {bucket.rate} requests per {self.per} seconds",
                    "retry_after": self.per,
                },
                headers={
                    "X-RateLimit-Limit": str(bucket.rate),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + self.per)),
                    "Retry-After": str(self.per),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(bucket.rate)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.per))

        return response


def create_rate_limiter_middleware(app, rate_limit: int = None, per: int = 60):
    """Factory function to create rate limiter middleware with settings.

    Args:
        app: FastAPI application.
        rate_limit: Optional fixed rate limit. If None, reads from settings dynamically.
        per: Time period in seconds.

    Returns:
        RateLimiterMiddleware instance.
    """
    if rate_limit is not None:
        rate_limit_getter = lambda: rate_limit
    else:
        rate_limit_getter = lambda: get_settings().rate_limit_per_minute
    return RateLimiterMiddleware(app, rate_limit_getter=rate_limit_getter, per=per)
