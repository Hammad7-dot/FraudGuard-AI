import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides):
    values = {
        "environment": "production",
        "api_key": "a" * 32,
        "database_url": "postgresql+psycopg2://user:password@db:5432/fraudguard",
        "cors_origins": ["https://fraudguard.example"],
    }
    values.update(overrides)
    return Settings(**values)


def test_production_requires_postgres_database():
    with pytest.raises(ValidationError, match="PostgreSQL"):
        production_settings(database_url="sqlite:///./fraudguard.db")


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS"):
        production_settings(cors_origins=["*"])


def test_production_requires_strong_api_key():
    with pytest.raises(ValidationError, match="32 characters"):
        production_settings(api_key="too-short")


def test_valid_production_settings_are_accepted():
    settings = production_settings()
    assert settings.environment == "production"
