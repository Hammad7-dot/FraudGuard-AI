"""Fraud analytics endpoints for dashboards."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.security import rate_limit, verify_api_key
from app.schemas.analytics import (CountryBreakdownResponse, FraudTrendsResponse, HighRiskResponse,
                                    ModelMetricsResponse, OverviewResponse, RuleEngineResponse,
                                    TransactionListResponse)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(rate_limit)])


@router.get("/overview", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)) -> OverviewResponse:
    return AnalyticsService(db).overview()


@router.get("/fraud-trends", response_model=FraudTrendsResponse)
def fraud_trends(
    hours: int = 24, db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)
) -> FraudTrendsResponse:
    return AnalyticsService(db).fraud_trends(hours=hours)


@router.get("/high-risk", response_model=HighRiskResponse)
def high_risk(
    limit: int = 50, db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)
) -> HighRiskResponse:
    return AnalyticsService(db).high_risk(limit=limit)


@router.get("/transactions", response_model=TransactionListResponse)
def recent_transactions(
    limit: int = 200, db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)
) -> TransactionListResponse:
    return AnalyticsService(db).recent_transactions(limit=limit)


@router.get("/by-country", response_model=CountryBreakdownResponse)
def by_country(
    limit: int = 500, db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)
) -> CountryBreakdownResponse:
    return AnalyticsService(db).country_breakdown(limit=limit)


@router.get("/model-metrics", response_model=ModelMetricsResponse)
def model_metrics(
    db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)
) -> ModelMetricsResponse:
    return AnalyticsService(db).model_metrics()


@router.get("/rules", response_model=RuleEngineResponse)
def rule_engine_info(
    db: Session = Depends(get_db_session), _api_key: str = Depends(verify_api_key)
) -> RuleEngineResponse:
    return AnalyticsService(db).rule_engine_info()
