"""Orchestrates the full transaction scoring pipeline."""
from __future__ import annotations

import json
import time
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.core.logging import get_logger
from app.ml.model_registry import ModelRegistry
from app.models.device import Device
from app.models.fraud_reason import FraudReason
from app.models.risk_assessment import RiskAssessment
from app.models.transaction import Transaction
from app.models.user import User
from app.rules.rule_engine import evaluate_rules
from app.schemas.transaction import AnalystFeedbackRequest, TransactionCreate, TransactionResponse
from app.services.explanation_service import build_reasons
from app.services.feature_service import FeatureService
from app.services.risk_aggregator import aggregate_risk
from app.streaming.redis_client import RedisClient

logger = get_logger(__name__)


class TransactionService:
    def __init__(self, db: Session, redis_client: RedisClient, settings: Optional[Settings] = None) -> None:
        self.db = db
        self.redis_client = redis_client
        self.settings = settings or get_settings()
        self.feature_service = FeatureService(db, redis_client)
        self.registry = ModelRegistry.instance()

    def process_transaction(self, tx: TransactionCreate) -> TransactionResponse:
        start = time.perf_counter()

        if self.db.get(Transaction, tx.transaction_id) is not None:
            raise ValidationFailedError(f"transaction_id '{tx.transaction_id}' already exists")

        features = self.feature_service.build_features(tx)

        fraud_probability = self.registry.xgb_model.predict_proba(features.vector())
        anomaly_score = self.registry.iso_model.anomaly_score(features.vector())
        rule_result = evaluate_rules(features, self.settings)

        risk = aggregate_risk(fraud_probability, anomaly_score, rule_result.rule_score, self.settings)

        reasons = build_reasons(
            features, rule_result.triggered_rules, fraud_probability, anomaly_score, self.registry.shap_explainer
        )

        # Persist transaction
        db_tx = Transaction(
            transaction_id=tx.transaction_id,
            user_id=tx.user_id,
            amount=tx.amount,
            currency=tx.currency,
            merchant_id=tx.merchant_id,
            merchant_category=tx.merchant_category,
            country=tx.country,
            device_id=tx.device_id,
            timestamp=tx.timestamp,
        )
        self.db.add(db_tx)

        # Upsert user
        user = self.db.query(User).filter(User.user_id == tx.user_id).one_or_none()
        if user is None:
            user = User(user_id=tx.user_id, avg_transaction_amount=tx.amount, transaction_count=1)
            self.db.add(user)
        else:
            total = user.avg_transaction_amount * user.transaction_count + tx.amount
            user.transaction_count += 1
            user.avg_transaction_amount = total / user.transaction_count

        # Upsert device
        device = (
            self.db.query(Device)
            .filter(Device.user_id == tx.user_id, Device.device_id == tx.device_id)
            .one_or_none()
        )
        if device is None:
            device = Device(user_id=tx.user_id, device_id=tx.device_id, transaction_count=1)
            self.db.add(device)
        else:
            device.transaction_count += 1

        elapsed_ms = (time.perf_counter() - start) * 1000

        risk_row = RiskAssessment(
            transaction_id=tx.transaction_id,
            user_id=tx.user_id,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            decision=risk.decision,
            fraud_probability=fraud_probability,
            anomaly_score=anomaly_score,
            rule_score=rule_result.rule_score,
            triggered_rules=json.dumps(rule_result.triggered_rules),
            model_version=self.registry.xgb_model.version,
            processing_time_ms=elapsed_ms,
        )
        self.db.add(risk_row)

        for reason in reasons:
            self.db.add(FraudReason(transaction_id=tx.transaction_id, reason=reason))

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValidationFailedError(f"transaction_id '{tx.transaction_id}' already exists")

        # Update real-time Redis state after commit succeeds
        self.feature_service.record_transaction_state(tx)

        return TransactionResponse(
            transaction_id=tx.transaction_id,
            user_id=tx.user_id,
            amount=tx.amount,
            currency=tx.currency,
            merchant_id=tx.merchant_id,
            merchant_category=tx.merchant_category,
            country=tx.country,
            device_id=tx.device_id,
            timestamp=tx.timestamp,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            decision=risk.decision,
            fraud_probability=round(fraud_probability, 4),
            anomaly_score=round(anomaly_score, 4),
            reasons=reasons,
            processing_time_ms=round(elapsed_ms, 3),
        )

    def get_transaction(self, transaction_id: str) -> TransactionResponse:
        db_tx = self.db.get(Transaction, transaction_id)
        if db_tx is None:
            raise NotFoundError(f"transaction '{transaction_id}' not found")
        risk_row = (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.transaction_id == transaction_id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )
        reasons = [r.reason for r in self.db.query(FraudReason).filter(FraudReason.transaction_id == transaction_id)]
        return TransactionResponse(
            transaction_id=db_tx.transaction_id,
            user_id=db_tx.user_id,
            amount=db_tx.amount,
            currency=db_tx.currency,
            merchant_id=db_tx.merchant_id,
            merchant_category=db_tx.merchant_category,
            country=db_tx.country,
            device_id=db_tx.device_id,
            timestamp=db_tx.timestamp,
            risk_score=risk_row.risk_score if risk_row else 0.0,
            risk_level=risk_row.risk_level if risk_row else "LOW",
            decision=risk_row.decision if risk_row else "APPROVE",
            fraud_probability=risk_row.fraud_probability if risk_row else 0.0,
            anomaly_score=risk_row.anomaly_score if risk_row else 0.0,
            reasons=reasons,
            processing_time_ms=risk_row.processing_time_ms if risk_row else 0.0,
            analyst_feedback=risk_row.analyst_feedback if risk_row else None,
        )

    def submit_feedback(self, transaction_id: str, feedback_req: AnalystFeedbackRequest) -> TransactionResponse:
        db_tx = self.db.get(Transaction, transaction_id)
        if db_tx is None:
            raise NotFoundError(f"transaction '{transaction_id}' not found")
        
        risk_row = (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.transaction_id == transaction_id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )
        if risk_row:
            risk_row.analyst_feedback = feedback_req.feedback
            risk_row.analyst_notes = feedback_req.notes
            self.db.commit()
            self.db.refresh(risk_row)

        return self.get_transaction(transaction_id)
