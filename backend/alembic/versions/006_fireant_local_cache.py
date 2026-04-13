"""Bảng cache Fireant cục bộ (131 mã) — giá ngày, fundamental, BCTC quý

Revision ID: 006
Revises: 005
Create Date: 2026-04-05
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fireant_symbol",
        sa.Column("symbol", sa.String(16), primary_key=True),
        sa.Column("universe_131", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("first_quote_date", sa.Date(), nullable=True),
        sa.Column("last_quote_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "fireant_quote_daily",
        sa.Column("symbol", sa.String(16), sa.ForeignKey("fireant_symbol.symbol", ondelete="CASCADE"), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("price_open", sa.Numeric(24, 6)),
        sa.Column("price_high", sa.Numeric(24, 6)),
        sa.Column("price_low", sa.Numeric(24, 6)),
        sa.Column("price_close", sa.Numeric(24, 6)),
        sa.Column("price_average", sa.Numeric(24, 6)),
        sa.Column("price_basic", sa.Numeric(24, 6)),
        sa.Column("total_volume", sa.Numeric(28, 4)),
        sa.Column("total_value", sa.Numeric(30, 4)),
        sa.Column("buy_foreign_quantity", sa.Numeric(28, 4)),
        sa.Column("sell_foreign_quantity", sa.Numeric(28, 4)),
        sa.Column("buy_foreign_value", sa.Numeric(30, 4)),
        sa.Column("sell_foreign_value", sa.Numeric(30, 4)),
        sa.Column("buy_quantity", sa.Numeric(28, 4)),
        sa.Column("sell_quantity", sa.Numeric(28, 4)),
        sa.Column("buy_count", sa.Integer()),
        sa.Column("sell_count", sa.Integer()),
        sa.Column("deal_volume", sa.Numeric(28, 4)),
        sa.Column("putthrough_volume", sa.Numeric(28, 4)),
        sa.Column("putthrough_value", sa.Numeric(30, 4)),
        sa.Column("prop_trading_net_value", sa.Numeric(30, 4)),
        sa.Column("prop_trading_net_deal_value", sa.Numeric(30, 4)),
        sa.Column("prop_trading_net_pt_value", sa.Numeric(30, 4)),
        sa.Column("current_foreign_room", sa.Numeric(24, 6)),
        sa.Column("adj_ratio", sa.Numeric(24, 10)),
        sa.Column("unit", sa.String(16)),
        sa.Column("source_ts", sa.DateTime(timezone=True)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fireant_quote_daily_trade_date", "fireant_quote_daily", ["trade_date"])
    op.create_index("ix_fireant_quote_daily_symbol_date", "fireant_quote_daily", ["symbol", "trade_date"])

    op.create_table(
        "fireant_fundamental",
        sa.Column("symbol", sa.String(16), sa.ForeignKey("fireant_symbol.symbol", ondelete="CASCADE"), primary_key=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("market_cap", sa.Numeric(30, 4)),
        sa.Column("pe", sa.Numeric(20, 6)),
        sa.Column("eps", sa.Numeric(20, 6)),
        sa.Column("shares_outstanding", sa.Numeric(28, 4)),
        sa.Column("foreign_ownership", sa.Numeric(12, 6)),
        sa.Column("free_shares", sa.Numeric(28, 4)),
        sa.Column("avg_volume_10d", sa.Numeric(28, 4)),
        sa.Column("avg_volume_3m", sa.Numeric(28, 4)),
        sa.Column("beta", sa.Numeric(12, 6)),
        sa.Column("high_52w", sa.Numeric(24, 6)),
        sa.Column("low_52w", sa.Numeric(24, 6)),
        sa.Column("price_change_1y", sa.Numeric(12, 6)),
        sa.Column("dividend", sa.Numeric(20, 6)),
        sa.Column("dividend_yield", sa.Numeric(12, 6)),
        sa.Column("sales_ttm", sa.Numeric(30, 4)),
        sa.Column("net_profit_ttm", sa.Numeric(30, 4)),
        sa.Column("company_type", sa.String(64)),
        sa.Column("insider_ownership", sa.Numeric(12, 6)),
        sa.Column("institution_ownership", sa.Numeric(12, 6)),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "fireant_financial_fact",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("fireant_symbol.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("period_label", sa.String(16), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("metric_code", sa.String(64), nullable=False),
        sa.Column("metric_name", sa.Text()),
        sa.Column("value_numeric", sa.Numeric(30, 4)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("symbol", "period_label", "metric_code", name="uq_fireant_fin_symbol_period_metric"),
    )
    op.create_index("ix_fireant_fin_symbol_period", "fireant_financial_fact", ["symbol", "period_end"])
    op.create_index("ix_fireant_fin_metric", "fireant_financial_fact", ["metric_code", "period_end"])

    op.create_table(
        "fireant_ingest_meta",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW fireant_v_sales_quarterly AS
        SELECT symbol, period_label, period_end, value_numeric AS sales
        FROM fireant_financial_fact
        WHERE metric_code = 'Sales'
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW fireant_v_netprofit_quarterly AS
        SELECT symbol, period_label, period_end, value_numeric AS net_profit
        FROM fireant_financial_fact
        WHERE metric_code = 'NetProfit'
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS fireant_v_netprofit_quarterly;")
    op.execute("DROP VIEW IF EXISTS fireant_v_sales_quarterly;")
    op.drop_table("fireant_ingest_meta")
    op.drop_table("fireant_financial_fact")
    op.drop_table("fireant_fundamental")
    op.drop_index("ix_fireant_quote_daily_symbol_date", table_name="fireant_quote_daily")
    op.drop_index("ix_fireant_quote_daily_trade_date", table_name="fireant_quote_daily")
    op.drop_table("fireant_quote_daily")
    op.drop_table("fireant_symbol")
