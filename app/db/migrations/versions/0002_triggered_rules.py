"""add triggered_rules column to risk_assessments

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "risk_assessments",
        sa.Column("triggered_rules", sa.Text, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("risk_assessments", "triggered_rules")
