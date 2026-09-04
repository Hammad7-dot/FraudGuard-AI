from datetime import datetime, timezone

from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    fraud_probability: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    rule_score: Mapped[float] = mapped_column(Float, nullable=False)
    triggered_rules: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    model_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    analyst_feedback: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    analyst_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, index=True, default=lambda: datetime.now(timezone.utc)
    )
