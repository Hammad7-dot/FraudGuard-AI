"""Aggregate analytics over stored transactions/risk assessments."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.fraud_reason import FraudReason
from app.models.risk_assessment import RiskAssessment
from app.models.transaction import Transaction
from app.schemas.analytics import (CountryBreakdownItem, CountryBreakdownResponse,
                                    FraudTrendsResponse, HighRiskItem, HighRiskResponse,
                                    ModelMetricsResponse, OverviewResponse, RuleEngineResponse,
                                    RuleInfo, TransactionListItem, TransactionListResponse,
                                    TrendPoint)
from app.schemas.risk import RiskAssessmentResponse, UserHistoryItem, UserRiskResponse


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def overview(self) -> OverviewResponse:
        total = self.db.query(func.count(RiskAssessment.id)).scalar() or 0
        blocked = self.db.query(func.count(RiskAssessment.id)).filter(RiskAssessment.decision == "BLOCK").scalar() or 0
        review = self.db.query(func.count(RiskAssessment.id)).filter(RiskAssessment.decision == "REVIEW").scalar() or 0
        approved = self.db.query(func.count(RiskAssessment.id)).filter(RiskAssessment.decision == "APPROVE").scalar() or 0
        high_risk = (
            self.db.query(func.count(RiskAssessment.id))
            .filter(RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"]))
            .scalar()
            or 0
        )
        avg_score = self.db.query(func.avg(RiskAssessment.risk_score)).scalar() or 0.0
        avg_time = self.db.query(func.avg(RiskAssessment.processing_time_ms)).scalar() or 0.0
        fraud_detected = blocked + review
        fraud_rate = (fraud_detected / total) if total else 0.0
        return OverviewResponse(
            total_transactions=total,
            fraud_detected=fraud_detected,
            fraud_rate=round(fraud_rate, 4),
            blocked=blocked,
            review=review,
            approved=approved,
            avg_risk_score=round(float(avg_score), 2),
            high_risk_count=high_risk,
            avg_processing_time_ms=round(float(avg_time), 3),
        )

    def fraud_trends(self, hours: int = 24) -> FraudTrendsResponse:
        since = datetime.utcnow() - timedelta(hours=hours)
        rows: List[RiskAssessment] = (
            self.db.query(RiskAssessment).filter(RiskAssessment.created_at >= since).all()
        )
        buckets: dict[str, list] = {}
        for row in rows:
            bucket = row.created_at.strftime("%Y-%m-%d %H:00")
            buckets.setdefault(bucket, []).append(row)

        points = []
        for bucket, items in sorted(buckets.items()):
            fraud_count = sum(1 for i in items if i.decision in ("BLOCK", "REVIEW"))
            avg_score = sum(i.risk_score for i in items) / len(items)
            points.append(
                TrendPoint(
                    bucket=bucket,
                    transaction_count=len(items),
                    fraud_count=fraud_count,
                    fraud_rate=round(fraud_count / len(items), 4) if items else 0.0,
                    avg_risk_score=round(avg_score, 2),
                )
            )
        return FraudTrendsResponse(points=points)

    def high_risk(self, limit: int = 50) -> HighRiskResponse:
        rows = (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"]))
            .order_by(RiskAssessment.risk_score.desc())
            .limit(limit)
            .all()
        )
        tx_ids = [row.transaction_id for row in rows]
        if tx_ids:
            tx_by_id = {
                tx.transaction_id: tx
                for tx in self.db.query(Transaction).filter(Transaction.transaction_id.in_(tx_ids))
            }
            reasons_by_tx: dict[str, list] = {}
            for r in self.db.query(FraudReason).filter(FraudReason.transaction_id.in_(tx_ids)):
                reasons_by_tx.setdefault(r.transaction_id, []).append(r.reason)
        else:
            tx_by_id = {}
            reasons_by_tx = {}

        items = []
        for row in rows:
            tx = tx_by_id.get(row.transaction_id)
            items.append(
                HighRiskItem(
                    transaction_id=row.transaction_id,
                    user_id=row.user_id,
                    amount=tx.amount if tx else 0.0,
                    risk_score=row.risk_score,
                    risk_level=row.risk_level,
                    decision=row.decision,
                    reasons=reasons_by_tx.get(row.transaction_id, []),
                )
            )
        return HighRiskResponse(items=items)

    def user_risk(self, user_id: str) -> UserRiskResponse:
        rows = self.db.query(RiskAssessment).filter(RiskAssessment.user_id == user_id).all()
        if not rows:
            raise NotFoundError(f"no history for user '{user_id}'")
        avg_score = sum(r.risk_score for r in rows) / len(rows)
        high_risk = sum(1 for r in rows if r.risk_level in ("HIGH", "CRITICAL"))
        blocked = sum(1 for r in rows if r.decision == "BLOCK")
        latest = max(rows, key=lambda r: r.created_at)
        return UserRiskResponse(
            user_id=user_id,
            average_risk_score=round(avg_score, 2),
            transaction_count=len(rows),
            high_risk_count=high_risk,
            blocked_count=blocked,
            latest_risk_level=latest.risk_level,
        )

    def user_history(self, user_id: str) -> List[UserHistoryItem]:
        rows = (
            self.db.query(Transaction, RiskAssessment)
            .join(RiskAssessment, RiskAssessment.transaction_id == Transaction.transaction_id)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.timestamp.desc())
            .all()
        )
        if not rows:
            raise NotFoundError(f"no history for user '{user_id}'")
        return [
            UserHistoryItem(
                transaction_id=tx.transaction_id,
                amount=tx.amount,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                decision=risk.decision,
                timestamp=tx.timestamp,
            )
            for tx, risk in rows
        ]

    def get_risk(self, transaction_id: str) -> RiskAssessmentResponse:
        row = (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.transaction_id == transaction_id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )
        if row is None:
            raise NotFoundError(f"no risk assessment for transaction '{transaction_id}'")
        reasons = [
            r.reason for r in self.db.query(FraudReason).filter(FraudReason.transaction_id == transaction_id)
        ]

        return RiskAssessmentResponse(
            transaction_id=row.transaction_id,
            risk_score=row.risk_score,
            risk_level=row.risk_level,
            decision=row.decision,
            fraud_probability=row.fraud_probability,
            anomaly_score=row.anomaly_score,
            rule_score=row.rule_score,
            triggered_rules=json.loads(row.triggered_rules or "[]"),
            reasons=reasons,
            model_version=row.model_version,
            created_at=row.created_at,
        )

    def recent_transactions(self, limit: int = 200) -> TransactionListResponse:
        rows = (
            self.db.query(Transaction, RiskAssessment)
            .join(RiskAssessment, RiskAssessment.transaction_id == Transaction.transaction_id)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
            .all()
        )
        items = [
            TransactionListItem(
                transaction_id=tx.transaction_id,
                user_id=tx.user_id,
                amount=tx.amount,
                currency=tx.currency,
                country=tx.country,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                decision=risk.decision,
                timestamp=tx.timestamp,
            )
            for tx, risk in rows
        ]
        return TransactionListResponse(items=items)

    def country_breakdown(self, limit: int = 500) -> CountryBreakdownResponse:
        rows = (
            self.db.query(Transaction, RiskAssessment)
            .join(RiskAssessment, RiskAssessment.transaction_id == Transaction.transaction_id)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
            .all()
        )
        buckets: dict[str, list] = {}
        for tx, risk in rows:
            buckets.setdefault(tx.country, []).append(risk)

        items = []
        for country, risks in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            fraud_count = sum(1 for r in risks if r.decision in ("BLOCK", "REVIEW"))
            avg_score = sum(r.risk_score for r in risks) / len(risks)
            items.append(
                CountryBreakdownItem(
                    country=country,
                    transaction_count=len(risks),
                    fraud_count=fraud_count,
                    fraud_rate=round(fraud_count / len(risks), 4),
                    avg_risk_score=round(avg_score, 2),
                )
            )
        return CountryBreakdownResponse(items=items)

    def model_metrics(self) -> ModelMetricsResponse:
        settings = get_settings()
        model_dir = settings.model_dir
        files = {
            "xgboost": f"fraud_xgboost_v{settings.xgboost_model_version}_metadata.json",
            "isolation_forest": f"isolation_forest_v{settings.isolation_forest_model_version}_metadata.json",
        }
        # metadata files are actually written without the version in the name; try both patterns
        fallback_files = {
            "xgboost": "fraud_xgboost_metadata.json",
            "isolation_forest": "isolation_forest_metadata.json",
        }
        models: dict[str, dict | None] = {}
        for key, fname in files.items():
            path = os.path.join(model_dir, fname)
            if not os.path.exists(path):
                path = os.path.join(model_dir, fallback_files[key])
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    models[key] = json.load(fh)
            else:
                models[key] = None
        return ModelMetricsResponse(models=models)

    def rule_engine_info(self) -> RuleEngineResponse:
        rules = [
            RuleInfo(
                name="LARGE_AMOUNT_OVER_10000",
                description="Transaction amount exceeds $10,000.",
                severity="HIGH",
            ),
            RuleInfo(
                name="HIGH_VELOCITY_5MIN",
                description="5 or more transactions from the same user within the last 5 minutes.",
                severity="HIGH",
            ),
            RuleInfo(
                name="NEW_DEVICE_LARGE_AMOUNT",
                description="A new/unrecognized device is used for an amount more than 5x the user's average.",
                severity="HIGH",
            ),
            RuleInfo(
                name="IMPOSSIBLE_TRAVEL",
                description="Consecutive transactions imply travel between locations faster than physically possible.",
                severity="CRITICAL",
            ),
        ]
        return RuleEngineResponse(rules=rules)
