"""Tracks devices used per user."""
from __future__ import annotations

from app.streaming.redis_client import DEVICES_TTL, RedisClient, safe_key_segment


class DeviceTracker:
    """Tracks devices associated with a user using Redis sets.

    Maintains a set of device IDs per user to detect new/unrecognized devices
    during transaction processing.
    """

    def __init__(self, redis_client: RedisClient) -> None:
        """Initialize the device tracker.

        Args:
            redis_client: Redis client instance for storing device data.
        """
        self.redis = redis_client

    def record_device(self, user_id: str, device_id: str) -> None:
        """Record a device as seen for a user.

        Args:
            user_id: Unique identifier for the user.
            device_id: Unique identifier for the device.
        """
        key = f"fraud:user:{safe_key_segment(user_id)}:devices"
        self.redis.sadd(key, device_id, DEVICES_TTL)

    def is_new_device(self, user_id: str, device_id: str) -> bool:
        """Check if a device is new (not previously seen) for a user.

        Args:
            user_id: Unique identifier for the user.
            device_id: Unique identifier for the device.

        Returns:
            True if the device has not been seen before for this user, False otherwise.
        """
        key = f"fraud:user:{safe_key_segment(user_id)}:devices"
        return device_id not in self.redis.smembers(key)

    def device_count(self, user_id: str) -> int:
        """Get the number of unique devices seen for a user.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            Count of unique devices associated with the user.
        """
        key = f"fraud:user:{safe_key_segment(user_id)}:devices"
        return self.redis.scard(key)
