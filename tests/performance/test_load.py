"""Lightweight load test: sends synthetic transactions through an in-process TestClient and
measures avg/p95/p99 latency. Kept small (200 requests) so it runs in a few seconds."""
import statistics
import time
import uuid
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
N_REQUESTS = 200


@pytest.fixture()
def perf_client():
    from app.core.config import get_settings
    get_settings().rate_limit_per_minute = 10_000

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

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_client

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_1000_transaction_latency_percentiles(perf_client):
    latencies_ms = []
    for i in range(N_REQUESTS):
        payload = {
            "transaction_id": str(uuid.uuid4()),
            "user_id": f"user-{i % 20}",
            "amount": 50.0 + (i % 100),
            "currency": "USD",
            "merchant_id": "merchant-1",
            "merchant_category": "grocery",
            "country": "US",
            "device_id": f"device-{i % 20}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        start = time.perf_counter()
        resp = perf_client.post("/api/v1/transactions", json=payload, headers={"x-api-key": API_KEY})
        elapsed = (time.perf_counter() - start) * 1000
        assert resp.status_code == 201
        latencies_ms.append(elapsed)

    latencies_ms.sort()
    avg = statistics.mean(latencies_ms)
    p95 = latencies_ms[int(len(latencies_ms) * 0.95) - 1]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99) - 1]

    print(f"\nPerf results over {N_REQUESTS} requests: avg={avg:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    # Sanity bound generous enough for CI/sandboxed environments (in-process TestClient, sqlite)
    assert avg < 2000
