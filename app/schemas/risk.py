"""Pydantic schemas for risk endpoints."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    transaction_id: str
    risk_score: float
    risk_level: str
    decision: str
    fraud_probability: float
    anomaly_score: float
    rule_score: float
    triggered_rules: List[str]
    reasons: List[str]
    model_version: str
    created_at: Optional[datetime] = None


class UserRiskResponse(BaseModel):
    user_id: str
    average_risk_score: float
    transaction_count: int
    high_risk_count: int
    blocked_count: int
    latest_risk_level: Optional[str] = None


class UserHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    amount: float
    risk_score: float
    risk_level: str
    decision: str
    timestamp: datetime
