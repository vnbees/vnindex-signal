"""Drop d10/d20 from signal_pnl_summary materialized view — T+3 only

Revision ID: 005
Revises: 004
Create Date: 2026-04-03
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS signal_pnl_summary;")
    op.execute(
        """
        CREATE MATERIALIZED VIEW signal_pnl_summary AS
        SELECT
            s.id AS signal_id,
            ar.portfolio_kind,
            s.run_date, s.symbol, s.score_total, s.recommendation, s.status,
            s.price_close_signal_date,
            s.price_open_t1,
            s.market_cap_bil,
            s.has_corporate_action,
            pt_3.pnl_pct  AS pnl_d3,
            pt_latest.pnl_pct AS latest_pnl_pct
        FROM signals s
        INNER JOIN analysis_runs ar ON ar.id = s.run_id
        LEFT JOIN price_tracking pt_3 ON pt_3.signal_id = s.id AND pt_3.days_after = 3
        LEFT JOIN LATERAL (
            SELECT pnl_pct FROM price_tracking
            WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1
        ) pt_latest ON TRUE;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_signal_pnl_summary_signal_id ON signal_pnl_summary (signal_id);"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS signal_pnl_summary;")
    op.execute(
        """
        CREATE MATERIALIZED VIEW signal_pnl_summary AS
        SELECT
            s.id AS signal_id,
            ar.portfolio_kind,
            s.run_date, s.symbol, s.score_total, s.recommendation, s.status,
            s.price_close_signal_date,
            s.price_open_t1,
            s.market_cap_bil,
            s.has_corporate_action,
            pt_3.pnl_pct  AS pnl_d3,
            pt_10.pnl_pct AS pnl_d10,
            pt_20.pnl_pct AS pnl_d20,
            pt_latest.pnl_pct AS latest_pnl_pct
        FROM signals s
        INNER JOIN analysis_runs ar ON ar.id = s.run_id
        LEFT JOIN price_tracking pt_3  ON pt_3.signal_id = s.id AND pt_3.days_after = 3
        LEFT JOIN price_tracking pt_10 ON pt_10.signal_id = s.id AND pt_10.days_after = 10
        LEFT JOIN price_tracking pt_20 ON pt_20.signal_id = s.id AND pt_20.days_after = 20
        LEFT JOIN LATERAL (
            SELECT pnl_pct FROM price_tracking
            WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1
        ) pt_latest ON TRUE;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_signal_pnl_summary_signal_id ON signal_pnl_summary (signal_id);"
    )
