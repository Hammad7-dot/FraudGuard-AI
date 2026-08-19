"""Builds human-readable reasons from rules, SHAP values, and feature deviations."""
from __future__ import annotations

from typing import List, Optional

from app.ml.shap_explainer import ShapExplainer
from app.services.feature_service import FEATURE_ORDER, FeatureBundle

RULE_MESSAGES = {
    "LARGE_AMOUNT_OVER_10000": "Transaction amount exceeds $10,000",
    "HIGH_VELOCITY_5MIN": "5 or more transactions in the last 5 minutes",
    "NEW_DEVICE_LARGE_AMOUNT": "New/unrecognized device used for an unusually large amount",
    "IMPOSSIBLE_TRAVEL": "Transaction location implies impossible travel speed from previous location",
}

FEATURE_LABELS = {
    "amount": "transaction amount",
    "amount_deviation": "deviation from average transaction amount",
    "transactions_last_5_minutes": "recent transaction velocity (5 min)",
    "transactions_last_15_minutes": "recent transaction velocity (15 min)",
    "new_device": "use of a new device",
    "device_transaction_count": "device transaction history",
    "country_changed": "change of country",
    "distance_from_previous_transaction": "distance from previous transaction location",
    "impossible_travel": "impossible travel pattern",
}


def build_reasons(
    features: FeatureBundle,
    triggered_rules: List[str],
    fraud_probability: float,
    anomaly_score: float,
    explainer: Optional[ShapExplainer] = None,
) -> List[str]:
    """Build human-readable risk reasons for a transaction.

    Combines rule-based messages, SHAP feature contributions (if available),
    and heuristic fallbacks to produce a list of explanatory strings.

    Args:
        features: Computed feature bundle for the transaction.
        triggered_rules: List of rule IDs that were triggered.
        fraud_probability: ML classifier fraud probability (0-1).
        anomaly_score: Isolation forest anomaly score (0-1).
        explainer: Optional SHAP explainer for model feature attribution.

    Returns:
        List of human-readable reason strings.
    """
    reasons: List[str] = []

    for rule in triggered_rules:
        reasons.append(RULE_MESSAGES.get(rule, rule))

    if explainer and explainer.available:
        contributions = explainer.top_contributions(features.vector(), FEATURE_ORDER, top_n=3)
        for name, value in contributions:
            if abs(value) < 1e-4:
                continue
            direction = "increased" if value > 0 else "decreased"
            label = FEATURE_LABELS.get(name, name)
            reasons.append(f"Model signal: {label} {direction} the fraud probability")
    else:
        # Fallback heuristic explanations based on notable feature deviations
        if features.values.get("amount_deviation", 0) > 2:
            reasons.append("Amount is significantly higher than the user's typical spend")
        if features.values.get("new_device", 0) == 1.0:
            reasons.append("Transaction made from a device not previously seen for this user")
        if features.values.get("country_changed", 0) == 1.0:
            reasons.append("Transaction country differs from the user's last known location")

    if fraud_probability > 0.7:
        reasons.append(f"ML classifier estimates high fraud probability ({fraud_probability:.2f})")
    if anomaly_score > 0.7:
        reasons.append(f"Anomaly detector flagged this transaction as highly unusual ({anomaly_score:.2f})")

    if not reasons:
        reasons.append("No significant risk indicators detected")

    return reasons
