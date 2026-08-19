"""Combines ML + anomaly + rule scores into a unified 0-100 risk score and decision."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass
class RiskResult:
    """Result of risk aggregation.

    Attributes:
        risk_score: Combined risk score (0-100).
        risk_level: Risk level category (LOW, MEDIUM, HIGH, CRITICAL).
        decision: Recommended action (APPROVE, REVIEW, BLOCK).
    """
    risk_score: float
    risk_level: str
    decision: str


def aggregate_risk(
    fraud_probability: float,
    anomaly_score: float,
    rule_score: float,
    settings: Settings,
) -> RiskResult:
    """Aggregate ML, anomaly, and rule scores into a unified risk assessment.

    Weighted combination:
    - ML fraud probability: 50% weight
    - Anomaly score: 25% weight
    - Rule score: 25% weight

    Args:
        fraud_probability: ML classifier fraud probability (0-1).
        anomaly_score: Isolation forest anomaly score (0-1).
        rule_score: Rule engine score (0-1).
        settings: Application settings containing risk thresholds.

    Returns:
        RiskResult with computed score, level, and decision.
    """
    risk_score = fraud_probability * 50 + anomaly_score * 25 + rule_score * 25
    risk_score = max(0.0, min(100.0, risk_score))

    if risk_score <= settings.risk_low_max:
        level = "LOW"
    elif risk_score <= settings.risk_medium_max:
        level = "MEDIUM"
    elif risk_score <= settings.risk_high_max:
        level = "HIGH"
    else:
        level = "CRITICAL"

    if level == "LOW":
        decision = "APPROVE"
    elif level == "MEDIUM":
        decision = "REVIEW" if risk_score >= settings.risk_review_threshold else "APPROVE"
    elif level == "HIGH":
        decision = "REVIEW"
    else:
        decision = "BLOCK"

    return RiskResult(risk_score=round(risk_score, 2), risk_level=level, decision=decision)
