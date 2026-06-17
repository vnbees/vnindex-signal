from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import settings
from database import AsyncSessionLocal
from routers import (
    automation,
    balanced_data,
    export,
    feedback,
    health,
    newsfeed_comments,
    price_updates,
    review_v2,
    signal_entries,
    signals,
    stats,
    stock_positions,
)
from services.daily_runner_scheduler import DailyRunnerScheduler

limiter = Limiter(key_func=get_remote_address)
scheduler = DailyRunnerScheduler()

app = FastAPI(
    title="VNINDEX Signal API",
    description="API for HOSE stock signals and PnL tracking",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(signals.router)
app.include_router(price_updates.router)
app.include_router(stats.router)
app.include_router(export.router)
app.include_router(feedback.router)
app.include_router(balanced_data.router)
app.include_router(signal_entries.router)
app.include_router(review_v2.router)
app.include_router(newsfeed_comments.router)
app.include_router(automation.router)
app.include_router(stock_positions.router)

@app.on_event("startup")
async def ensure_feedback_table_exists():
    # Safety net for environments where Alembic migration wasn't run yet.
    create_feedback_sql = """
    CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL,
        name VARCHAR(200) NULL,
        contact VARCHAR(200) NULL,
        page_url TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    create_index_sql = """
    CREATE INDEX IF NOT EXISTS ix_feedback_created_at
    ON feedback (created_at);
    """
    create_signal_entries_sql = """
    CREATE TABLE IF NOT EXISTS signal_entries (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(16) NULL,
        reference_date DATE NULL,
        title VARCHAR(200) NULL,
        notes TEXT NULL,
        payload JSONB NULL,
        data_extracted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    signal_indexes = [
        "CREATE INDEX IF NOT EXISTS ix_signal_entries_symbol ON signal_entries (symbol);",
        "CREATE INDEX IF NOT EXISTS ix_signal_entries_deleted_at ON signal_entries (deleted_at);",
        "CREATE INDEX IF NOT EXISTS ix_signal_entries_reference_date ON signal_entries (reference_date);",
        "CREATE INDEX IF NOT EXISTS ix_signal_entries_data_extracted ON signal_entries (data_extracted);",
    ]
    async with AsyncSessionLocal() as session:
        await session.execute(text(create_feedback_sql))
        await session.execute(text(create_index_sql))
        await session.execute(text(create_signal_entries_sql))
        for stmt in signal_indexes:
            await session.execute(text(stmt))
        create_newsfeed_comments_sql = """
        CREATE TABLE IF NOT EXISTS newsfeed_comments (
            id SERIAL PRIMARY KEY,
            signal_entry_id INTEGER NOT NULL REFERENCES signal_entries(id) ON DELETE CASCADE,
            commenter_id UUID NOT NULL,
            display_name VARCHAR(80) NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        );
        """
        newsfeed_comment_indexes = [
            "CREATE INDEX IF NOT EXISTS ix_newsfeed_comments_signal_entry_id ON newsfeed_comments (signal_entry_id);",
            "CREATE INDEX IF NOT EXISTS ix_newsfeed_comments_commenter_id ON newsfeed_comments (commenter_id);",
            "CREATE INDEX IF NOT EXISTS ix_newsfeed_comments_deleted_at ON newsfeed_comments (deleted_at);",
        ]
        await session.execute(text(create_newsfeed_comments_sql))
        for stmt in newsfeed_comment_indexes:
            await session.execute(text(stmt))
        create_stock_positions_sql = """
        CREATE TABLE IF NOT EXISTS stock_positions (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(16) NOT NULL,
            signal_date DATE NOT NULL,
            valuation_price NUMERIC(14, 2) NULL,
            buy_price NUMERIC(14, 2) NOT NULL,
            sell_price NUMERIC(14, 2) NULL,
            sell_date DATE NULL,
            current_price NUMERIC(14, 2) NULL,
            price_as_of DATE NULL,
            unrealized_pnl_pct NUMERIC(10, 4) NULL,
            realized_pnl_pct NUMERIC(10, 4) NULL,
            pnl_3d_pct NUMERIC(10, 4) NULL,
            pnl_5d_pct NUMERIC(10, 4) NULL,
            pnl_10d_pct NUMERIC(10, 4) NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
        stock_position_indexes = [
            "CREATE INDEX IF NOT EXISTS ix_stock_positions_symbol ON stock_positions (symbol);",
            "CREATE INDEX IF NOT EXISTS ix_stock_positions_signal_date ON stock_positions (signal_date);",
            "CREATE INDEX IF NOT EXISTS ix_stock_positions_sell_date ON stock_positions (sell_date);",
        ]
        await session.execute(text(create_stock_positions_sql))
        for stmt in stock_position_indexes:
            await session.execute(text(stmt))
        await session.commit()
    await scheduler.start()


@app.on_event("shutdown")
async def stop_daily_scheduler():
    await scheduler.stop()

@app.get("/")
async def root():
    return {"message": "VNINDEX Signal API", "docs": "/docs"}
