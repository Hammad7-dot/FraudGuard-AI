from app.rules.rule_engine import evaluate_rules
from app.services.feature_service import FeatureBundle


def make_features(**overrides):
    base = {
        "amount": 100.0,
        "avg_transaction_amount": 100.0,
        "transactions_last_5_minutes": 0.0,
        "new_device": 0.0,
        "impossible_travel": 0.0,
    }
    base.update(overrides)
    return FeatureBundle(values=base)


def test_large_amount_triggers_high_risk():
    result = evaluate_rules(make_features(amount=15000))
    assert "LARGE_AMOUNT_OVER_10000" in result.triggered_rules
    assert result.rule_score >= 0.6


def test_high_velocity_triggers_rule():
    result = evaluate_rules(make_features(transactions_last_5_minutes=6))
    assert "HIGH_VELOCITY_5MIN" in result.triggered_rules


def test_new_device_large_amount_triggers_rule():
    result = evaluate_rules(make_features(new_device=1.0, avg_transaction_amount=50, amount=500))
    assert "NEW_DEVICE_LARGE_AMOUNT" in result.triggered_rules


def test_impossible_travel_triggers_critical():
    result = evaluate_rules(make_features(impossible_travel=1.0))
    assert "IMPOSSIBLE_TRAVEL" in result.triggered_rules
    assert result.rule_score == 1.0


def test_no_rules_triggered_for_normal_transaction():
    result = evaluate_rules(make_features())
    assert result.triggered_rules == []
    assert result.rule_score == 0.0
