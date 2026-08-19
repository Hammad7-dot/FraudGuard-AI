"""Health and readiness endpoints."""
import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_redis
from app.core.config import get_settings
from app.streaming.redis_client import RedisClient, CircuitState

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Basic health check - returns OK if service is running."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db_session), redis_client: RedisClient = Depends(get_redis)) -> dict:
    """Readiness check - verifies database and Redis connectivity."""
    db_ok = True
    db_latency_ms = None
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - start) * 1000, 2)
    except Exception:
        db_ok = False

    redis_ok = redis_client.available
    redis_circuit_state = redis_client.circuit_state.value if hasattr(redis_client, 'circuit_state') else "unknown"

    overall_ready = db_ok and redis_ok
    status = "ready" if overall_ready else "degraded"

    return {
        "status": status,
        "checks": {
            "database": {
                "status": "ok" if db_ok else "failed",
                "latency_ms": db_latency_ms,
            },
            "redis": {
                "status": "ok" if redis_ok else "failed",
                "circuit_breaker": redis_circuit_state,
            },
        },
    }


@router.get("/live")
def live() -> dict:
    """Liveness check - returns OK if process is alive (for Kubernetes liveness probe)."""
    return {"status": "alive"}


@router.get("/version")
def version() -> dict:
    """Version information endpoint."""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "xgboost_model_version": settings.xgboost_model_version,
        "isolation_forest_model_version": settings.isolation_forest_model_version,
    }
