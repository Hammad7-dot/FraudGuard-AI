from datetime import datetime, timezone

from app.streaming.velocity_tracker import VelocityTracker


def test_same_timestamp_transactions_remain_distinct(fake_redis_client):
    tracker = VelocityTracker(fake_redis_client)
    timestamp = datetime.now(timezone.utc)

    tracker.record("user-1", "tx-1", 10.0, timestamp)
    tracker.record("user-1", "tx-2", 10.0, timestamp)

    count_5m, _, _, amount_1h = tracker.preview("user-1", "tx-3", 10.0, timestamp)
    assert count_5m == 3
    assert amount_1h == 30.0


def test_record_is_idempotent_by_transaction_id(fake_redis_client):
    tracker = VelocityTracker(fake_redis_client)
    timestamp = datetime.now(timezone.utc)

    tracker.record("user-1", "tx-1", 10.0, timestamp)
    tracker.record("user-1", "tx-1", 10.0, timestamp)

    count_5m, _, _, amount_1h = tracker.preview("user-1", "tx-2", 5.0, timestamp)
    assert count_5m == 2
    assert amount_1h == 15.0
