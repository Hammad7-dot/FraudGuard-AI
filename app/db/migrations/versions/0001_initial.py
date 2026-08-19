"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("avg_transaction_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("transaction_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.String(100), nullable=False, index=True),
        sa.Column("user_id", sa.String(100), nullable=False, index=True),
        sa.Column("first_seen", sa.DateTime, nullable=False),
        sa.Column("transaction_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(100), primary_key=True),
        sa.Column("user_id", sa.String(100), nullable=False, index=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("merchant_id", sa.String(100), nullable=False),
        sa.Column("merchant_category", sa.String(100), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(100), nullable=False, index=True),
        sa.Column("user_id", sa.String(100), nullable=False, index=True),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("fraud_probability", sa.Float, nullable=False),
        sa.Column("anomaly_score", sa.Float, nullable=False),
        sa.Column("rule_score", sa.Float, nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("processing_time_ms", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "fraud_reasons",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(100), nullable=False, index=True),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fraud_reasons")
    op.drop_table("risk_assessments")
    op.drop_table("transactions")
    op.drop_table("devices")
    op.drop_table("users")
