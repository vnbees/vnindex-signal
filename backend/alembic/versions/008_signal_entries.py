"""signal_entries: quản lý tín hiệu (thực thể mới) + soft delete + cờ trích xuất

Revision ID: 008
Revises: 007
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "data_extracted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_signal_entries_symbol", "signal_entries", ["symbol"])
    op.create_index("ix_signal_entries_deleted_at", "signal_entries", ["deleted_at"])
    op.create_index(
        "ix_signal_entries_reference_date", "signal_entries", ["reference_date"]
    )
    op.create_index(
        "ix_signal_entries_data_extracted", "signal_entries", ["data_extracted"]
    )


def downgrade() -> None:
    op.drop_index("ix_signal_entries_data_extracted", table_name="signal_entries")
    op.drop_index("ix_signal_entries_reference_date", table_name="signal_entries")
    op.drop_index("ix_signal_entries_deleted_at", table_name="signal_entries")
    op.drop_index("ix_signal_entries_symbol", table_name="signal_entries")
    op.drop_table("signal_entries")
