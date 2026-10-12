"""Redis client wrapper that degrades gracefully when Redis is unreachable.

Key naming convention (documented per rules.md):
- fraud:user:{id}:transactions  -> sorted set of transaction timestamps (epoch seconds), TTL 1h
- fraud:user:{id}:amounts       -> sorted set of "timestamp:amount" entries, TTL 1h
- fraud:user:{id}:devices       -> set of device ids seen for user, TTL 30d
- fraud:user:{id}:last_location -> hash {lat, lon, country, timestamp}, TTL 7d
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, cast

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_UNSAFE_KEY_CHARS = re.compile(r"[^A-Za-z0-9_.\-]")


def safe_key_segment(value: str) -> str:
    """Sanitize an untrusted value (e.g. user_id/device_id) for use inside a Redis key.

    Strips characters that could let a crafted id (e.g. containing ':') collide with
    or traverse into a different key namespace, and caps length via a hash fallback.
    """
    cleaned = _UNSAFE_KEY_CHARS.sub("", value)
    if not cleaned or len(cleaned) > 200:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    return cleaned


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests go through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker for Redis operations.

    Prevents cascading failures by stopping requests to a failing service
    and automatically attempting recovery after a timeout.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._expected_exception = expected_exception
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time and \
               time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open")
        return self._state

    def record_success(self) -> None:
        """Record a successful operation."""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("circuit_breaker_closed")
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened failure_count=%d", self._failure_count)

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: Function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func(*args, **kwargs).

        Raises:
            Exception: If circuit is open or func raises an unexpected exception.
        """
        if self.state == CircuitState.OPEN:
            raise redis.ConnectionError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self._expected_exception:
            self.record_failure()
            raise


TRANSACTIONS_TTL = 3600
AMOUNTS_TTL = 3600
DEVICES_TTL = 60 * 60 * 24 * 30
LOCATION_TTL = 60 * 60 * 24 * 7


class RedisClient:
    """Thin wrapper around redis-py that never raises on connection failure.

    Implements a circuit breaker pattern to prevent cascading failures
    when Redis is unavailable, with automatic recovery attempts.
    """

    _RECONNECT_INTERVAL = 30.0

    def __init__(self) -> None:
        self._settings = get_settings()
        self._available = True
        self._last_reconnect_attempt = 0.0
        self._client: Optional[redis.Redis] = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=redis.RedisError,
        )
        self._connect()

    def _connect(self) -> None:
        try:
            self._client = redis.Redis.from_url(
                self._settings.redis_url,
                socket_timeout=self._settings.redis_socket_timeout,
                socket_connect_timeout=self._settings.redis_socket_timeout,
                decode_responses=True,
            )
            self._client.ping()
            self._available = True
            self._circuit_breaker.record_success()
        except Exception as exc:  # pragma: no cover - depends on environment
            logger.warning("redis_unavailable error=%s falling back to no-op mode", exc)
            self._client = None
            self._available = False
            self._circuit_breaker.record_failure()
        self._last_reconnect_attempt = time.monotonic()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._circuit_breaker.state

    def _safe(self, fn: Callable[..., T], default: Optional[T] = None) -> Optional[T]:
        """Execute a function safely with circuit breaker and reconnection logic.

        Args:
            fn: Function to execute.
            default: Default value to return on failure.

        Returns:
            Result of fn() or default on failure.
        """
        if not self._client:
            now = time.monotonic()
            if now - self._last_reconnect_attempt < self._RECONNECT_INTERVAL:
                return default
            self._connect()
            if not self._client:
                return default

        try:
            return self._circuit_breaker.call(fn)
        except redis.RedisError as exc:  # pragma: no cover
            logger.warning("redis_op_failed error=%s", exc)
            return default
        except Exception as exc:  # pragma: no cover
            logger.warning("redis_op_unexpected_error error=%s", exc)
            return default

    def zadd(self, key: str, mapping: dict, ttl: int) -> None:
        def op():
            pipe = cast(redis.Redis, self._client).pipeline()
            pipe.zadd(key, mapping)
            pipe.expire(key, ttl)
            pipe.execute()
        self._safe(op)

    def zrangebyscore(self, key: str, min_score: float, max_score: float) -> list:
        return self._safe(
            lambda: cast(redis.Redis, self._client).zrangebyscore(key, min_score, max_score),
            default=[],
        ) or []

    def atomic(self, build_fn: Callable) -> list:
        """Run build_fn(pipe) against a transactional pipeline and return pipe.execute() results.

        redis-py pipelines default to transaction=True (MULTI/EXEC), so every command queued by
        build_fn executes as one atomic, isolated batch — no other client can observe a partial
        write, and a write can be combined with a read of its own effect in the same round trip.
        """
        def op():
            pipe = cast(redis.Redis, self._client).pipeline()
            build_fn(pipe)
            return pipe.execute()
        return self._safe(op, default=[]) or []

    def sadd(self, key: str, value: str, ttl: int) -> None:
        def op():
            pipe = cast(redis.Redis, self._client).pipeline()
            pipe.sadd(key, value)
            pipe.expire(key, ttl)
            pipe.execute()
        self._safe(op)

    def smembers(self, key: str) -> set:
        return self._safe(lambda: cast(redis.Redis, self._client).smembers(key), default=set()) or set()

    def scard(self, key: str) -> int:
        return self._safe(lambda: cast(redis.Redis, self._client).scard(key), default=0) or 0

    def hset(self, key: str, mapping: dict, ttl: int) -> None:
        def op():
            pipe = cast(redis.Redis, self._client).pipeline()
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, ttl)
            pipe.execute()
        self._safe(op)

    def hgetall(self, key: str) -> dict:
        return self._safe(lambda: cast(redis.Redis, self._client).hgetall(key), default={}) or {}


_client_singleton: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = RedisClient()
    return _client_singleton
