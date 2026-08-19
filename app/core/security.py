"""API key auth + simple in-memory rate limiting."""
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError, UnauthorizedError

_request_log: Dict[str, Deque[float]] = defaultdict(deque)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.require_api_key:
        return "anonymous"
    if not x_api_key or x_api_key != settings.api_key:
        raise UnauthorizedError("invalid or missing API key")
    return x_api_key


def rate_limit(request: Request) -> None:
    settings = get_settings()
    client_id = request.headers.get("x-api-key") or (request.client.host if request.client else "unknown")
    now = time.time()
    window = 60.0
    bucket = _request_log[client_id]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        raise RateLimitedError("rate limit exceeded")
    bucket.append(now)
