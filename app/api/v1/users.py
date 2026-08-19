"""Per-user risk summary and history endpoints."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.security import rate_limit, verify_api_key
from app.schemas.risk import UserHistoryItem, UserRiskResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(rate_limit)])


@router.get("/{user_id}/risk", response_model=UserRiskResponse)
def get_user_risk(
    user_id: str,
    db: Session = Depends(get_db_session),
    _api_key: str = Depends(verify_api_key),
) -> UserRiskResponse:
    service = AnalyticsService(db)
    return service.user_risk(user_id)


@router.get("/{user_id}/history", response_model=List[UserHistoryItem])
def get_user_history(
    user_id: str,
    db: Session = Depends(get_db_session),
    _api_key: str = Depends(verify_api_key),
) -> List[UserHistoryItem]:
    service = AnalyticsService(db)
    return service.user_history(user_id)
