"""portfolio_kind on analysis_runs; signals unique (run_id, symbol); MV by signal_id

Revision ID: 004
Revises: 003
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE signals s
        SET run_id = ar.id
        FROM analysis_runs ar
        WHERE s.run_id IS NULL AND s.run_date = ar.run_date
        """
    )
    op.alter_column(
        "signals",
        "run_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.add_column(
        "analysis_runs",
        sa.Column(
            "portfolio_kind",
            sa.String(length=20),
            nullable=False,
            server_default="top_cap",
        ),
    )
    op.drop_constraint("analysis_runs_run_date_key", "analysis_runs", type_="unique")
    op.create_unique_constraint(
        "uq_analysis_runs_run_date_portfolio_kind",
        "analysis_runs",
        ["run_date", "portfolio_kind"],
    )

    op.drop_constraint("uq_signals_run_date_symbol", "signals", type_="unique")
    op.create_unique_constraint(
        "uq_signals_run_id_symbol",
        "signals",
        ["run_id", "symbol"],
    )

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


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS signal_pnl_summary;")
    op.execute(
        """
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
        """
    )
    op.execute("CREATE UNIQUE INDEX ON signal_pnl_summary(run_date, symbol);")

    op.drop_constraint("uq_signals_run_id_symbol", "signals", type_="unique")
    op.create_unique_constraint(
        "uq_signals_run_date_symbol",
        "signals",
        ["run_date", "symbol"],
    )

    op.drop_constraint(
        "uq_analysis_runs_run_date_portfolio_kind", "analysis_runs", type_="unique"
    )
    op.create_unique_constraint("analysis_runs_run_date_key", "analysis_runs", ["run_date"])
    op.drop_column("analysis_runs", "portfolio_kind")

    op.alter_column(
        "signals",
        "run_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
