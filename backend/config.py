from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vnindex_signal"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/vnindex_signal"
    api_secret_key: str = "changeme"
    bcrypt_rounds: int = 12
    rate_limit_get: str = "60/minute"
    rate_limit_post: str = "10/minute"
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
