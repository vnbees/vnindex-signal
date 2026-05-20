"""stock_positions: sổ mua bán thủ công

Revision ID: 012
Revises: 011
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("valuation_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("buy_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("sell_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("sell_date", sa.Date(), nullable=True),
        sa.Column("current_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("price_as_of", sa.Date(), nullable=True),
        sa.Column("unrealized_pnl_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("realized_pnl_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("pnl_3d_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("pnl_5d_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("pnl_10d_pct", sa.Numeric(10, 4), nullable=True),
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
    op.create_index("ix_stock_positions_symbol", "stock_positions", ["symbol"])
    op.create_index("ix_stock_positions_signal_date", "stock_positions", ["signal_date"])
    op.create_index("ix_stock_positions_sell_date", "stock_positions", ["sell_date"])


def downgrade() -> None:
    op.drop_index("ix_stock_positions_sell_date", table_name="stock_positions")
    op.drop_index("ix_stock_positions_signal_date", table_name="stock_positions")
    op.drop_index("ix_stock_positions_symbol", table_name="stock_positions")
    op.drop_table("stock_positions")
