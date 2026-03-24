from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vnindex_signal"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/vnindex_signal"
    api_secret_key: str = "changeme"
    bcrypt_rounds: int = 12
    rate_limit_get: str = "60/minute"
    rate_limit_post: str = "10/minute"
    cors_origins: list[str] = ["http://localhost:3000"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-convert postgresql:// to postgresql+asyncpg:// for async support
        if self.database_url.startswith("postgresql://"):
            object.__setattr__(self, 'database_url', self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1))
        # Keep sync URL without asyncpg
        if self.database_url_sync.startswith("postgresql+asyncpg://"):
            object.__setattr__(self, 'database_url_sync', self.database_url_sync.replace("postgresql+asyncpg://", "postgresql://", 1))

    class Config:
        env_file = ".env"

settings = Settings()
