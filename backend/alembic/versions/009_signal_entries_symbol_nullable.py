"""signal_entries.symbol nullable — cho phép chỉ ghi chú, không bắt buộc mã CK

Revision ID: 009
Revises: 008
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "signal_entries",
        "symbol",
        existing_type=sa.String(length=16),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE signal_entries SET symbol = '-' WHERE symbol IS NULL OR symbol = ''"
    )
    op.alter_column(
        "signal_entries",
        "symbol",
        existing_type=sa.String(length=16),
        nullable=False,
    )
