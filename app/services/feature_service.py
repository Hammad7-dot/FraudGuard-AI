"""Builds the feature vector used by ML models and the rule engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate
from app.streaming.device_tracker import DeviceTracker
from app.streaming.location_tracker import LocationTracker
from app.streaming.redis_client import RedisClient
from app.streaming.velocity_tracker import VelocityTracker

FEATURE_SCHEMA_VERSION = "1.0.0"

FEATURE_ORDER = [
    "amount",
    "hour",
    "day_of_week",
    "avg_transaction_amount",
    "transaction_count_1h",
    "transaction_count_24h",
    "amount_deviation",
    "transactions_last_5_minutes",
    "transactions_last_15_minutes",
    "transactions_last_1_hour",
    "amount_last_1_hour",
    "new_device",
    "device_transaction_count",
    "country_changed",
    "distance_from_previous_transaction",
    "impossible_travel",
]


@dataclass
class FeatureBundle:
    """Container for computed feature values and metadata.

    Attributes:
        values: Dictionary mapping feature names to their computed float values.
        merchant_category: Merchant category of the transaction.
        country: Transaction country code.
        currency: Transaction currency code.
    """
    values: Dict[str, float] = field(default_factory=dict)
    merchant_category: str = ""
    country: str = ""
    currency: str = ""

    def vector(self) -> list[float]:
        """Return feature values as an ordered list matching FEATURE_ORDER.

        Returns:
            List of feature values in the order defined by FEATURE_ORDER.
        """
        return [float(self.values.get(name, 0.0)) for name in FEATURE_ORDER]

    def as_dict(self) -> Dict[str, float]:
        """Return feature values as a dictionary.

        Returns:
            Copy of the internal values dictionary.
        """
        return dict(self.values)


class FeatureService:
    """Service for building feature vectors from transaction data.

    Combines historical database statistics with real-time Redis-based
    velocity, device, and location tracking to produce a complete feature
    vector for ML model inference and rule evaluation.
    """

    def __init__(self, db: Session, redis_client: RedisClient) -> None:
        """Initialize the feature service.

        Args:
            db: SQLAlchemy database session for querying historical data.
            redis_client: Redis client for real-time velocity/device/location tracking.
        """
        self.db = db
        self.velocity = VelocityTracker(redis_client)
        self.devices = DeviceTracker(redis_client)
        self.locations = LocationTracker(redis_client)

    def _user_history_stats(self, user_id: str, ts: datetime) -> Dict[str, float]:
        """Compute historical statistics for a user from the database.

        Args:
            user_id: Unique identifier for the user.
            ts: Timestamp to compute stats up to (exclusive).

        Returns:
            Dictionary with keys:
            - avg_transaction_amount: Average transaction amount (float)
            - transaction_count_1h: Transaction count in last hour (capped at 999)
            - transaction_count_24h: Transaction count in last 24 hours (capped at 9999)
        """
        q = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        avg_amount = self.db.query(func.avg(Transaction.amount)).filter(
            Transaction.user_id == user_id
        ).scalar() or 0.0
        count_1h = q.filter(Transaction.timestamp >= ts - timedelta(hours=1), Transaction.timestamp < ts).count()
        count_24h = q.filter(Transaction.timestamp >= ts - timedelta(hours=24), Transaction.timestamp < ts).count()
        return {
            "avg_transaction_amount": float(avg_amount),
            "transaction_count_1h": float(min(count_1h, 999)),
            "transaction_count_24h": float(min(count_24h, 9999)),
        }

    def build_features(self, tx: TransactionCreate) -> FeatureBundle:
        """Build a complete feature vector for a transaction.

        Args:
            tx: Transaction data including user, amount, device, location, and timestamp.

        Returns:
            FeatureBundle containing all computed features and metadata.
        """
        ts = tx.timestamp
        user_stats = self._user_history_stats(tx.user_id, ts)
        avg_amount = user_stats["avg_transaction_amount"] or tx.amount
        amount_deviation = (tx.amount - avg_amount) / avg_amount if avg_amount else 0.0

        tx_5m, tx_15m, tx_1h, amt_1h = self.velocity.record_and_get_velocity(tx.user_id, tx.amount, ts)

        new_device = self.devices.is_new_device(tx.user_id, tx.device_id)
        device_count = self.devices.device_count(tx.user_id)

        country_changed, distance_km, impossible_travel = self.locations.evaluate(tx.user_id, tx.country, ts)

        values = {
            "amount": tx.amount,
            "hour": float(ts.hour),
            "day_of_week": float(ts.weekday()),
            "avg_transaction_amount": avg_amount,
            "transaction_count_1h": user_stats["transaction_count_1h"],
            "transaction_count_24h": user_stats["transaction_count_24h"],
            "amount_deviation": amount_deviation,
            "transactions_last_5_minutes": float(tx_5m),
            "transactions_last_15_minutes": float(tx_15m),
            "transactions_last_1_hour": float(tx_1h),
            "amount_last_1_hour": float(amt_1h),
            "new_device": 1.0 if new_device else 0.0,
            "device_transaction_count": float(device_count),
            "country_changed": 1.0 if country_changed else 0.0,
            "distance_from_previous_transaction": float(distance_km),
            "impossible_travel": 1.0 if impossible_travel else 0.0,
        }
        return FeatureBundle(
            values=values,
            merchant_category=tx.merchant_category,
            country=tx.country,
            currency=tx.currency,
        )

    def record_transaction_state(self, tx: TransactionCreate) -> None:
        """Update Redis real-time state after processing a transaction.

        Velocity is already recorded atomically as part of build_features() (see
        VelocityTracker.record_and_get_velocity); only device/location state remains here.

        Args:
            tx: Transaction data to record in Redis state.
        """
        self.devices.record_device(tx.user_id, tx.device_id)
        self.locations.record_location(tx.user_id, tx.country, tx.timestamp)
