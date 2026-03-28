"""add pnl_d3 to signal_pnl_summary (replace d1 and d5 with d3)

Revision ID: 002
Revises: 001
Create Date: 2026-03-28
"""
from alembic import op

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop and recreate materialized view with pnl_d3 replacing pnl_d1 and pnl_d5
    op.execute("DROP MATERIALIZED VIEW IF EXISTS signal_pnl_summary;")
    op.execute("""
        CREATE MATERIALIZED VIEW signal_pnl_summary AS
        SELECT
            s.id AS signal_id,
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
        LEFT JOIN price_tracking pt_3  ON pt_3.signal_id = s.id AND pt_3.days_after = 3
        LEFT JOIN price_tracking pt_10 ON pt_10.signal_id = s.id AND pt_10.days_after = 10
        LEFT JOIN price_tracking pt_20 ON pt_20.signal_id = s.id AND pt_20.days_after = 20
        LEFT JOIN LATERAL (
            SELECT pnl_pct FROM price_tracking
            WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1
        ) pt_latest ON TRUE;
    """)
    op.execute("CREATE UNIQUE INDEX ON signal_pnl_summary(run_date, symbol);")


def downgrade() -> None:
    # Restore original view with pnl_d1 and pnl_d5
    op.execute("DROP MATERIALIZED VIEW IF EXISTS signal_pnl_summary;")
    op.execute("""
        CREATE MATERIALIZED VIEW signal_pnl_summary AS
        SELECT
            s.id AS signal_id,
            s.run_date, s.symbol, s.score_total, s.recommendation, s.status,
            s.price_close_signal_date,
            s.price_open_t1,
            s.market_cap_bil,
            s.has_corporate_action,
            pt_1.pnl_pct  AS pnl_d1,
            pt_5.pnl_pct  AS pnl_d5,
            pt_10.pnl_pct AS pnl_d10,
            pt_20.pnl_pct AS pnl_d20,
            pt_latest.pnl_pct AS latest_pnl_pct
        FROM signals s
        LEFT JOIN price_tracking pt_1  ON pt_1.signal_id = s.id AND pt_1.days_after = 1
        LEFT JOIN price_tracking pt_5  ON pt_5.signal_id = s.id AND pt_5.days_after = 5
        LEFT JOIN price_tracking pt_10 ON pt_10.signal_id = s.id AND pt_10.days_after = 10
        LEFT JOIN price_tracking pt_20 ON pt_20.signal_id = s.id AND pt_20.days_after = 20
        LEFT JOIN LATERAL (
            SELECT pnl_pct FROM price_tracking
            WHERE signal_id = s.id ORDER BY days_after DESC LIMIT 1
        ) pt_latest ON TRUE;
    """)
    op.execute("CREATE UNIQUE INDEX ON signal_pnl_summary(run_date, symbol);")
