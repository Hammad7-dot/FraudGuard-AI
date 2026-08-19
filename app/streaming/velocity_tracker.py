"""Tracks per-user transaction velocity using Redis sorted sets."""
from __future__ import annotations

from datetime import datetime
from typing import Tuple

from app.streaming.redis_client import AMOUNTS_TTL, TRANSACTIONS_TTL, RedisClient, safe_key_segment


class VelocityTracker:
    """Tracks transaction velocity for a user using Redis sorted sets.

    Uses atomic Redis pipelines to record transactions and compute velocity
    metrics (counts over 5m, 15m, 1h windows and amount sum over 1h) in a
    single round-trip, avoiding read-then-write race conditions.
    """

    def __init__(self, redis_client: RedisClient) -> None:
        """Initialize the velocity tracker.

        Args:
            redis_client: Redis client instance for storing velocity data.
        """
        self.redis = redis_client

    def record_and_get_velocity(
        self, user_id: str, amount: float, ts: datetime
    ) -> Tuple[int, int, int, float]:
        """Atomically record a transaction and return velocity metrics.

        Args:
            user_id: Unique identifier for the user.
            amount: Transaction amount.
            ts: Transaction timestamp (timezone-aware).

        Returns:
            Tuple of (count_5m, count_15m, count_1h, amount_sum_1h) where:
            - count_5m: Number of transactions in the last 5 minutes
            - count_15m: Number of transactions in the last 15 minutes
            - count_1h: Number of transactions in the last hour
            - amount_sum_1h: Sum of transaction amounts in the last hour
        """
        epoch = ts.timestamp()
        key_tx = f"fraud:user:{safe_key_segment(user_id)}:transactions"
        key_amt = f"fraud:user:{safe_key_segment(user_id)}:amounts"
        now = epoch

        def build(pipe):
            pipe.zadd(key_tx, {str(epoch): epoch})
            pipe.expire(key_tx, TRANSACTIONS_TTL)
            pipe.zadd(key_amt, {f"{epoch}:{amount}": epoch})
            pipe.expire(key_amt, AMOUNTS_TTL)
            pipe.zcount(key_tx, now - 5 * 60, now)
            pipe.zcount(key_tx, now - 15 * 60, now)
            pipe.zcount(key_tx, now - 60 * 60, now)
            pipe.zrangebyscore(key_amt, now - 60 * 60, now)

        results = self.redis.atomic(build)
        if len(results) < 8:
            return 0, 0, 0, 0.0
        count_5m, count_15m, count_1h, amt_entries = results[4], results[5], results[6], results[7] or []
        amount_sum_1h = 0.0
        for entry in amt_entries:
            try:
                amount_sum_1h += float(entry.split(":")[-1])
            except (ValueError, IndexError):
                continue
        return count_5m, count_15m, count_1h, amount_sum_1h
