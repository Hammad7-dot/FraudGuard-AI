"""Shared FastAPI dependencies."""

from app.db.session import get_db
from app.streaming.redis_client import RedisClient, get_redis_client

get_db_session = get_db


def get_redis() -> RedisClient:
    return get_redis_client()
