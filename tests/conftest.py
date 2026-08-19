"""Shared pytest fixtures."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REQUIRE_API_KEY", "true")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest  # noqa: E402
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.session import Base  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.models import device, fraud_reason, risk_assessment, transaction, user  # noqa: F401
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def fake_redis_client():
    from app.streaming.redis_client import RedisClient, CircuitBreaker
    import time

    client = RedisClient.__new__(RedisClient)
    try:
        import fakeredis
        client._client = fakeredis.FakeRedis(decode_responses=True)
        client._available = True
    except ImportError:
        client._client = None
        client._available = False
    client._last_reconnect_attempt = time.monotonic()
    # Initialize circuit breaker for tests
    client._circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=30.0,
        expected_exception=Exception,
    )
    return client
