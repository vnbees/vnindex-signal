"""Balanced pipeline: profile cache, symbol posts, daily JSON snapshot

Revision ID: 010
Revises: 009
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fireant_symbol_profile",
        sa.Column("symbol", sa.String(16), sa.ForeignKey("fireant_symbol.symbol", ondelete="CASCADE"), primary_key=True),
        sa.Column("sector_display", sa.String(512), nullable=True),
        sa.Column("icb_code", sa.String(64), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "fireant_symbol_post",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("fireant_symbol.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("symbol", "external_id", name="uq_fireant_symbol_post_sym_ext"),
    )
    op.create_index("ix_fireant_symbol_post_symbol_pub", "fireant_symbol_post", ["symbol", "published_at"])

    op.create_table(
        "balanced_daily_snapshot",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("uq_balanced_daily_snapshot_as_of", "balanced_daily_snapshot", ["as_of_date"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_balanced_daily_snapshot_as_of", table_name="balanced_daily_snapshot")
    op.drop_table("balanced_daily_snapshot")
    op.drop_index("ix_fireant_symbol_post_symbol_pub", table_name="fireant_symbol_post")
    op.drop_table("fireant_symbol_post")
    op.drop_table("fireant_symbol_profile")
