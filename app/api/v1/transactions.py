"""Transaction ingestion and lookup endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, get_redis
from app.core.security import rate_limit, verify_api_key
from app.schemas.transaction import AnalystFeedbackRequest, TransactionCreate, TransactionResponse
from app.services.transaction_service import TransactionService
from app.streaming.redis_client import RedisClient

router = APIRouter(prefix="/transactions", tags=["transactions"], dependencies=[Depends(rate_limit)])


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db_session),
    redis_client: RedisClient = Depends(get_redis),
    _api_key: str = Depends(verify_api_key),
) -> TransactionResponse:
    service = TransactionService(db, redis_client)
    return service.process_transaction(payload)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db_session),
    redis_client: RedisClient = Depends(get_redis),
    _api_key: str = Depends(verify_api_key),
) -> TransactionResponse:
    service = TransactionService(db, redis_client)
    return service.get_transaction(transaction_id)

@router.post("/{transaction_id}/feedback", response_model=TransactionResponse)
def submit_analyst_feedback(
    transaction_id: str,
    payload: AnalystFeedbackRequest,
    db: Session = Depends(get_db_session),
    redis_client: RedisClient = Depends(get_redis),
    _api_key: str = Depends(verify_api_key),
) -> TransactionResponse:
    service = TransactionService(db, redis_client)
    return service.submit_feedback(transaction_id, payload)
