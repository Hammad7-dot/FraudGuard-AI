"""Tracks last known location per user and computes impossible-travel heuristics."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Tuple

from app.streaming.redis_client import LOCATION_TTL, RedisClient, safe_key_segment

# Very rough centroid lat/lon per ISO country code, enough for a demo heuristic.
COUNTRY_CENTROIDS: dict[str, Tuple[float, float]] = {
    "US": (39.8, -98.5),
    "GB": (54.0, -2.0),
    "FR": (46.6, 2.2),
    "DE": (51.2, 10.4),
    "IN": (22.0, 79.0),
    "CN": (35.0, 103.0),
    "JP": (36.2, 138.3),
    "AU": (-25.0, 133.0),
    "BR": (-10.0, -55.0),
    "CA": (56.1, -106.3),
    "RU": (61.5, 105.3),
    "NG": (9.1, 8.7),
    "ZA": (-30.6, 22.9),
    "MX": (23.6, -102.6),
    "AE": (23.4, 53.8),
    "SG": (1.35, 103.8),
}
MAX_PLAUSIBLE_KMH = 900.0  # ~commercial flight speed


def _haversine_km(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate the great-circle distance between two points on Earth.

    Args:
        p1: Tuple of (latitude, longitude) for the first point in degrees.
        p2: Tuple of (latitude, longitude) for the second point in degrees.

    Returns:
        Distance in kilometers between the two points.
    """
    lat1, lon1 = p1
    lat2, lon2 = p2
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class LocationTracker:
    """Tracks user location history and evaluates impossible-travel scenarios.

    Stores the last known location (country centroid) per user in Redis and
    computes distance/speed heuristics to detect physically impossible travel
    between consecutive transactions.
    """

    def __init__(self, redis_client: RedisClient) -> None:
        """Initialize the location tracker.

        Args:
            redis_client: Redis client instance for storing location data.
        """
        self.redis = redis_client

    def get_last_location(self, user_id: str) -> Optional[dict]:
        """Retrieve the last recorded location for a user.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            Dictionary with keys 'lat', 'lon', 'country', 'timestamp' if found,
            None otherwise.
        """
        key = f"fraud:user:{safe_key_segment(user_id)}:last_location"
        data = self.redis.hgetall(key)
        return data or None

    def record_location(self, user_id: str, country: str, ts: datetime) -> None:
        """Record the current location for a user.

        Args:
            user_id: Unique identifier for the user.
            country: ISO country code (e.g., 'US', 'GB').
            ts: Transaction timestamp (timezone-aware).
        """
        key = f"fraud:user:{safe_key_segment(user_id)}:last_location"
        lat, lon = COUNTRY_CENTROIDS.get(country, (0.0, 0.0))
        self.redis.hset(
            key,
            {"lat": lat, "lon": lon, "country": country, "timestamp": ts.timestamp()},
            LOCATION_TTL,
        )

    def evaluate(
        self, user_id: str, country: str, ts: datetime
    ) -> Tuple[bool, float, bool]:
        """Evaluate location change and impossible travel for a transaction.

        Args:
            user_id: Unique identifier for the user.
            country: ISO country code of the current transaction.
            ts: Transaction timestamp (timezone-aware).

        Returns:
            Tuple of (country_changed, distance_km, impossible_travel) where:
            - country_changed: True if country differs from last known location
            - distance_km: Great-circle distance from last location in km
            - impossible_travel: True if travel speed exceeds MAX_PLAUSIBLE_KMH
        """
        last = self.get_last_location(user_id)
        if not last:
            return False, 0.0, False
        prev_country = last.get("country")
        country_changed = bool(prev_country) and prev_country != country
        try:
            prev_lat, prev_lon = float(last["lat"]), float(last["lon"])
            prev_ts = float(last["timestamp"])
        except (KeyError, ValueError, TypeError):
            return country_changed, 0.0, False

        cur_lat, cur_lon = COUNTRY_CENTROIDS.get(country, (0.0, 0.0))
        distance_km = _haversine_km((prev_lat, prev_lon), (cur_lat, cur_lon))
        elapsed_hours = max((ts.timestamp() - prev_ts) / 3600.0, 1e-6)
        speed_kmh = distance_km / elapsed_hours
        impossible_travel = country_changed and speed_kmh > MAX_PLAUSIBLE_KMH
        return country_changed, distance_km, impossible_travel
