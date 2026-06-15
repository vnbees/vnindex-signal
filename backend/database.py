from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings


def _connect_args() -> dict:
    """Railway private Postgres (postgres.railway.internal) không dùng TLS."""
    url = settings.database_url
    if "railway.internal" in url or "sslmode=disable" in url:
        return {"ssl": False}
    return {}


engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args(),
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
