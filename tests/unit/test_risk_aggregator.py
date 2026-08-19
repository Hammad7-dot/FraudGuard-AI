from app.core.config import Settings
from app.services.risk_aggregator import aggregate_risk


def settings():
    return Settings(_env_file=None)


def test_low_risk_approve():
    result = aggregate_risk(0.05, 0.05, 0.0, settings())
    assert result.risk_level == "LOW"
    assert result.decision == "APPROVE"


def test_critical_risk_block():
    result = aggregate_risk(0.95, 0.9, 1.0, settings())
    assert result.risk_score == 95.0
    assert result.risk_level == "CRITICAL"
    assert result.decision == "BLOCK"


def test_medium_risk_review_threshold():
    result = aggregate_risk(0.9, 0.0, 0.0, settings())  # 0.9*50 = 45
    assert result.risk_level == "MEDIUM"
    assert result.decision == "REVIEW"


def test_medium_risk_approve_below_threshold():
    result = aggregate_risk(0.6, 0.0, 0.0, settings())  # 0.6*50 = 30
    assert result.risk_level == "MEDIUM"
    assert result.decision == "APPROVE"


def test_high_risk_review():
    result = aggregate_risk(1.0, 0.5, 0.4, settings())  # 50 + 12.5 + 10 = 72.5
    assert result.risk_level == "HIGH"
    assert result.decision == "REVIEW"


def test_score_clamped_to_100():
    result = aggregate_risk(1.0, 1.0, 1.0, settings())
    assert result.risk_score == 100.0
