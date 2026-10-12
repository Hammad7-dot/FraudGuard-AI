from datetime import datetime, timedelta, timezone

from app.schemas.transaction import TransactionCreate
from app.services.feature_service import FEATURE_ORDER, FeatureService


def build_tx(**overrides):
    base = dict(
        transaction_id="tx-1",
        user_id="user-1",
        amount=100.0,
        currency="usd",
        merchant_id="m-1",
        merchant_category="grocery",
        country="us",
        device_id="d-1",
        timestamp=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return TransactionCreate(**base)


def test_currency_and_country_uppercased():
    tx = build_tx()
    assert tx.currency == "USD"
    assert tx.country == "US"


def test_feature_vector_has_expected_length(db_session, fake_redis_client):
    service = FeatureService(db_session, fake_redis_client)
    tx = build_tx()
    features = service.build_features(tx)
    assert len(features.vector()) == len(FEATURE_ORDER)
    assert features.values["amount"] == 100.0


def test_new_device_detected_for_first_transaction(db_session, fake_redis_client):
    service = FeatureService(db_session, fake_redis_client)
    tx = build_tx()
    features = service.build_features(tx)
    assert features.values["new_device"] == 1.0


def test_device_not_new_after_recording(db_session, fake_redis_client):
    service = FeatureService(db_session, fake_redis_client)
    tx = build_tx()
    service.record_transaction_state(tx)
    features = service.build_features(tx)
    assert features.values["new_device"] == 0.0


def test_amount_validation_rejects_non_positive():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        build_tx(amount=-5)


def test_timestamp_must_be_timezone_aware():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="timezone-aware"):
        build_tx(timestamp=datetime.now())


def test_timestamp_rejects_future_clock_skew():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="future"):
        build_tx(timestamp=datetime.now(timezone.utc) + timedelta(minutes=10))


def test_unknown_country_has_no_geographic_signal(db_session, fake_redis_client):
    service = FeatureService(db_session, fake_redis_client)
    previous = build_tx(country="US", transaction_id="previous")
    service.record_transaction_state(previous)

    features = service.build_features(build_tx(country="ZZ", transaction_id="unknown"))

    assert features.values["distance_from_previous_transaction"] == 0.0
    assert features.values["impossible_travel"] == 0.0


def test_build_features_does_not_mutate_velocity(db_session, fake_redis_client):
    service = FeatureService(db_session, fake_redis_client)
    tx = build_tx()

    first = service.build_features(tx)
    second = service.build_features(tx)

    assert first.values["transactions_last_5_minutes"] == 1.0
    assert second.values["transactions_last_5_minutes"] == 1.0
