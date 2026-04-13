"""Thêm bảng fireant_financial_indicator (REST financial-indicators)

Revision ID: 007
Revises: 006
Create Date: 2026-04-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fireant_financial_indicator",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("fireant_symbol.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("short_name", sa.String(256), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metric_group", sa.Integer(), nullable=True),
        sa.Column("group_name", sa.Text(), nullable=True),
        sa.Column("value", sa.Numeric(28, 10), nullable=True),
        sa.Column("value_change", sa.Numeric(28, 10), nullable=True),
        sa.Column("industry_value", sa.Numeric(28, 10), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("symbol", "short_name", name="uq_fireant_fin_ind_symbol_short"),
    )
    op.create_index("ix_fireant_fin_ind_symbol", "fireant_financial_indicator", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_fireant_fin_ind_symbol", table_name="fireant_financial_indicator")
    op.drop_table("fireant_financial_indicator")
