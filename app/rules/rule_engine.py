"""Deterministic fraud rule engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.config import Settings, get_settings
from app.services.feature_service import FeatureBundle

HIGH_RISK_WEIGHT = 0.6
CRITICAL_RISK_WEIGHT = 1.0


@dataclass
class RuleResult:
    rule_score: float
    triggered_rules: List[str] = field(default_factory=list)


def evaluate_rules(features: FeatureBundle, settings: Optional[Settings] = None) -> RuleResult:
    settings = settings or get_settings()
    values = features.values
    triggered: List[str] = []
    score = 0.0

    if values.get("amount", 0.0) > settings.rule_large_amount_threshold:
        triggered.append("LARGE_AMOUNT_OVER_10000")
        score = max(score, HIGH_RISK_WEIGHT)

    if values.get("transactions_last_5_minutes", 0.0) >= settings.rule_high_velocity_5min_count:
        triggered.append("HIGH_VELOCITY_5MIN")
        score = max(score, HIGH_RISK_WEIGHT)

    avg_amount = values.get("avg_transaction_amount", 0.0)
    if (
        values.get("new_device", 0.0) == 1.0
        and avg_amount > 0
        and values.get("amount", 0.0) > avg_amount * settings.rule_new_device_amount_multiplier
    ):
        triggered.append("NEW_DEVICE_LARGE_AMOUNT")
        score = max(score, HIGH_RISK_WEIGHT)

    if values.get("impossible_travel", 0.0) == 1.0:
        triggered.append("IMPOSSIBLE_TRAVEL")
        score = max(score, CRITICAL_RISK_WEIGHT)

    return RuleResult(rule_score=min(score, 1.0), triggered_rules=triggered)
