from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import settings
from database import AsyncSessionLocal
from routers import health, signals, price_updates, stats, export, feedback

limiter = Limiter(key_func=get_remote_address)

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
        await session.commit()

@app.get("/")
async def root():
    return {"message": "VNINDEX Signal API", "docs": "/docs"}
