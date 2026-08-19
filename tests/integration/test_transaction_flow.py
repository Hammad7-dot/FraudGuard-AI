from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db_session, get_redis
from app.db.session import Base
from app.main import app

API_KEY = "test-api-key"


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.models import device, fraud_reason, risk_assessment, transaction, user  # noqa: F401
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    from app.streaming.redis_client import RedisClient, CircuitBreaker
    import time
    fake_client = RedisClient.__new__(RedisClient)
    try:
        import fakeredis
        fake_client._client = fakeredis.FakeRedis(decode_responses=True)
        fake_client._available = True
    except ImportError:
        fake_client._client = None
        fake_client._available = False
    fake_client._last_reconnect_attempt = time.monotonic()
    # Initialize circuit breaker for tests
    fake_client._circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=30.0,
        expected_exception=Exception,
    )

    def override_get_redis():
        return fake_client

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def sample_payload(**overrides):
    base = {
        "transaction_id": "tx-int-1",
        "user_id": "user-int-1",
        "amount": 250.0,
        "currency": "USD",
        "merchant_id": "merchant-1",
        "merchant_category": "electronics",
        "country": "US",
        "device_id": "device-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def test_health_endpoint(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready_endpoint(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert data["checks"]["database"]["status"] == "ok"
    assert data["checks"]["redis"]["status"] == "ok"


def test_create_transaction_without_api_key_rejected(client):
    resp = client.post("/api/v1/transactions", json=sample_payload())
    assert resp.status_code == 401


def test_create_transaction_returns_risk_score(client):
    resp = client.post(
        "/api/v1/transactions", json=sample_payload(), headers={"x-api-key": API_KEY}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert data["decision"] in ("APPROVE", "REVIEW", "BLOCK")
    assert "reasons" in data
    assert data["processing_time_ms"] >= 0


def test_invalid_transaction_returns_400(client):
    payload = sample_payload(amount=-5)
    resp = client.post("/api/v1/transactions", json=payload, headers={"x-api-key": API_KEY})
    assert resp.status_code == 422 or resp.status_code == 400


def test_duplicate_transaction_rejected(client):
    payload = sample_payload(transaction_id="tx-dup")
    r1 = client.post("/api/v1/transactions", json=payload, headers={"x-api-key": API_KEY})
    assert r1.status_code == 201
    r2 = client.post("/api/v1/transactions", json=payload, headers={"x-api-key": API_KEY})
    assert r2.status_code == 400


def test_get_transaction_by_id(client):
    payload = sample_payload(transaction_id="tx-get-1")
    client.post("/api/v1/transactions", json=payload, headers={"x-api-key": API_KEY})
    resp = client.get("/api/v1/transactions/tx-get-1", headers={"x-api-key": API_KEY})
    assert resp.status_code == 200
    assert resp.json()["transaction_id"] == "tx-get-1"


def test_get_missing_transaction_404(client):
    resp = client.get("/api/v1/transactions/does-not-exist", headers={"x-api-key": API_KEY})
    assert resp.status_code == 404


def test_large_amount_leads_to_higher_risk(client):
    payload = sample_payload(transaction_id="tx-large", amount=50000)
    resp = client.post("/api/v1/transactions", json=payload, headers={"x-api-key": API_KEY})
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_score"] >= 15  # LARGE_AMOUNT rule contributes at least 0.6*25=15
    assert data["decision"] in ("APPROVE", "REVIEW", "BLOCK")


def test_analytics_overview_reflects_transactions(client):
    client.post("/api/v1/transactions", json=sample_payload(transaction_id="tx-a1"), headers={"x-api-key": API_KEY})
    resp = client.get("/api/v1/analytics/overview", headers={"x-api-key": API_KEY})
    assert resp.status_code == 200
    assert resp.json()["total_transactions"] >= 1


def test_user_risk_endpoint(client):
    client.post(
        "/api/v1/transactions",
        json=sample_payload(transaction_id="tx-u1", user_id="user-history"),
        headers={"x-api-key": API_KEY},
    )
    resp = client.get("/api/v1/users/user-history/risk", headers={"x-api-key": API_KEY})
    assert resp.status_code == 200
    assert resp.json()["transaction_count"] == 1
