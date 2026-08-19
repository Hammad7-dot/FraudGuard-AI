"""Pydantic schemas for analytics endpoints."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_transactions: int
    fraud_detected: int
    fraud_rate: float
    blocked: int
    review: int
    approved: int
    avg_risk_score: float
    high_risk_count: int
    avg_processing_time_ms: float


class TrendPoint(BaseModel):
    bucket: str
    transaction_count: int
    fraud_count: int
    fraud_rate: float
    avg_risk_score: float


class FraudTrendsResponse(BaseModel):
    points: List[TrendPoint]


class HighRiskItem(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    risk_score: float
    risk_level: str
    decision: str
    reasons: List[str]


class HighRiskResponse(BaseModel):
    items: List[HighRiskItem]


class TransactionListItem(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    country: str
    risk_score: float
    risk_level: str
    decision: str
    timestamp: datetime


class TransactionListResponse(BaseModel):
    items: List[TransactionListItem]


class CountryBreakdownItem(BaseModel):
    country: str
    transaction_count: int
    fraud_count: int
    fraud_rate: float
    avg_risk_score: float


class CountryBreakdownResponse(BaseModel):
    items: List[CountryBreakdownItem]


class ModelMetricsResponse(BaseModel):
    models: Dict[str, Optional[Dict[str, Any]]]


class RuleInfo(BaseModel):
    name: str
    description: str
    severity: str


class RuleEngineResponse(BaseModel):
    rules: List[RuleInfo]
