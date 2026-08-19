"""Risk assessment lookup endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.security import rate_limit, verify_api_key
from app.schemas.risk import RiskAssessmentResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/risk", tags=["risk"], dependencies=[Depends(rate_limit)])


@router.get("/{transaction_id}", response_model=RiskAssessmentResponse)
def get_risk(
    transaction_id: str,
    db: Session = Depends(get_db_session),
    _api_key: str = Depends(verify_api_key),
) -> RiskAssessmentResponse:
    service = AnalyticsService(db)
    return service.get_risk(transaction_id)
