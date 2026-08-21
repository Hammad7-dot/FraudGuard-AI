"""Application configuration via environment variables."""
from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", protected_namespaces=("settings_",)
    )

    app_name: str = "FraudGuard AI"
    environment: str = "development"
    log_level: str = "INFO"

    # DB: defaults to sqlite for easy local dev; use Postgres in prod via DATABASE_URL
    database_url: str = "sqlite:///./fraudguard.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_socket_timeout: float = 0.5

    # Security
    api_key: str = ""
    require_api_key: bool = True
    rate_limit_per_minute: int = 120

    @model_validator(mode="after")
    def _check_api_key_configured(self) -> "Settings":
        if self.require_api_key and not self.api_key:
            raise ValueError(
                "API_KEY must be set when REQUIRE_API_KEY is true (no insecure default allowed)"
            )
        return self

    # Risk thresholds
    risk_low_max: int = 29
    risk_medium_max: int = 59
    risk_high_max: int = 79
    risk_review_threshold: int = 45  # within MEDIUM band, >= this -> REVIEW

    # Rule engine thresholds
    rule_large_amount_threshold: float = 10_000.0
    rule_high_velocity_5min_count: int = 5
    rule_new_device_amount_multiplier: float = 5.0

    # Model versions
    xgboost_model_version: str = "1.0.0"
    isolation_forest_model_version: str = "1.0.0"
    model_dir: str = "data/models"

    # Misc
    cors_origins: List[str] = ["*"]
    max_request_bytes: int = 1_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
