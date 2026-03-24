"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # trading_calendar - stores ALL days (365/year), is_trading=FALSE for weekends/holidays
    op.create_table('trading_calendar',
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('is_trading', sa.Boolean(), nullable=False, server_default='TRUE'),
        sa.Column('note', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('trade_date')
    )

    op.create_table('analysis_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_date', sa.Date(), nullable=False),
        sa.Column('top_n', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('hold_days', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_date')
    )

    op.create_table('signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('run_date', sa.Date(), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('score_financial', sa.Integer(), nullable=False),
        sa.Column('score_seasonal', sa.Integer(), nullable=False),
        sa.Column('score_technical', sa.Integer(), nullable=False),
        sa.Column('score_cashflow', sa.Integer(), nullable=False),
        sa.Column('score_total', sa.Integer(), nullable=False),
        sa.Column('recommendation', sa.String(20), nullable=False),
        sa.Column('signal_type', sa.String(10), nullable=False),
        sa.Column('price_close_signal_date', sa.Numeric(12, 2), nullable=False),
        sa.Column('price_open_t1', sa.Numeric(12, 2), nullable=True),
        sa.Column('market_cap_bil', sa.Numeric(15, 2), nullable=True),
        sa.Column('has_corporate_action', sa.Boolean(), server_default='FALSE'),
        sa.Column('detail_financial', postgresql.JSONB(), nullable=True),
        sa.Column('detail_technical', postgresql.JSONB(), nullable=True),
        sa.Column('detail_cashflow', postgresql.JSONB(), nullable=True),
        sa.Column('detail_seasonal', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['run_id'], ['analysis_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_date', 'symbol', name='uq_signals_run_date_symbol')
    )
    op.create_index('idx_signals_run_date', 'signals', ['run_date'], postgresql_using='btree', postgresql_ops={'run_date': 'DESC'})
    op.create_index('idx_signals_symbol', 'signals', ['symbol'])
    op.create_index('idx_signals_recommendation', 'signals', ['recommendation'])
    op.create_index('idx_signals_status', 'signals', ['status'])

    # Trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER signals_updated_at
            BEFORE UPDATE ON signals
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    op.create_table('price_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.Column('run_date', sa.Date(), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('track_date', sa.Date(), nullable=False),
        sa.Column('days_after', sa.Integer(), nullable=False),
        sa.Column('price_close', sa.Numeric(12, 2), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('signal_id', 'track_date', name='uq_price_tracking_signal_date')
    )
    op.create_index('idx_price_tracking_signal_days', 'price_tracking', ['signal_id', 'days_after'])
    op.create_index('idx_price_tracking_dates', 'price_tracking', ['run_date', 'track_date'])

    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(72), nullable=False),
        sa.Column('label', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='TRUE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )

    op.create_table('audit_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('run_date', sa.Date(), nullable=True),
        sa.Column('symbol', sa.String(10), nullable=True),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_created', 'audit_log', ['created_at'], postgresql_ops={'created_at': 'DESC'})

    # Materialized view with LATERAL JOIN (not correlated subquery)
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

def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS signal_pnl_summary;")
    op.drop_table('audit_log')
    op.drop_table('api_keys')
    op.drop_table('price_tracking')
    op.execute("DROP TRIGGER IF EXISTS signals_updated_at ON signals;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at;")
    op.drop_table('signals')
    op.drop_table('analysis_runs')
    op.drop_table('trading_calendar')
