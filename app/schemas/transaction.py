"""Pydantic schemas for transaction I/O."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):
    transaction_id: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    merchant_id: str = Field(..., min_length=1, max_length=100)
    merchant_category: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=2)
    device_id: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("country")
    @classmethod
    def upper_country(cls, v: str) -> str:
        normalized = v.upper()
        if not normalized.isascii() or not normalized.isalpha():
            raise ValueError("country must be a two-letter ISO-style code")
        return normalized

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        now = datetime.now(timezone.utc)
        normalized = value.astimezone(timezone.utc)
        if normalized > now + timedelta(minutes=5):
            raise ValueError("timestamp cannot be more than 5 minutes in the future")
        if normalized < now - timedelta(days=30):
            raise ValueError("timestamp cannot be more than 30 days old")
        return normalized


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    country: str
    device_id: str
    timestamp: datetime
    risk_score: float
    risk_level: str
    decision: str
    fraud_probability: float
    anomaly_score: float
    reasons: List[str]
    processing_time_ms: float
    analyst_feedback: Optional[str] = None

class AnalystFeedbackRequest(BaseModel):
    feedback: str = Field(..., pattern="^(CONFIRMED_FRAUD|FALSE_POSITIVE|LEGITIMATE)$")
    notes: Optional[str] = None


class TransactionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    country: str
    device_id: str
    timestamp: datetime
