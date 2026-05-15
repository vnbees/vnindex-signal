from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vnindex_signal"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/vnindex_signal"
    api_secret_key: str = "changeme"
    bcrypt_rounds: int = 12
    rate_limit_get: str = "60/minute"
    rate_limit_post: str = "10/minute"
    cors_origins: list[str] = ["http://localhost:3000"]
    # Railway gán trên service backend, trỏ tới public URL của frontend (vd. www.viistock.io.vn).
    railway_service_frontend_url: str | None = None
    automation_token: str | None = None
    automation_base_url: str = "https://vnindex-signal-production.up.railway.app"
    google_gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    automation_http_timeout_seconds: int = 120
    automation_allow_force_rerun: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-convert postgresql:// to postgresql+asyncpg:// for async support
        if self.database_url.startswith("postgresql://"):
            object.__setattr__(
                self,
                "database_url",
                self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1),
            )
        # Keep sync URL without asyncpg
        if self.database_url_sync.startswith("postgresql+asyncpg://"):
            object.__setattr__(
                self,
                "database_url_sync",
                self.database_url_sync.replace("postgresql+asyncpg://", "postgresql://", 1),
            )

        # Tránh lệch CORS khi đổi custom domain nhưng quên cập nhật CORS_ORIGINS.
        origins = list(self.cors_origins)

        def add_origin(origin: str) -> None:
            o = origin.rstrip("/")
            if o and o not in origins:
                origins.append(o)

        raw = (self.railway_service_frontend_url or "").strip()
        if raw:
            if raw.startswith("http://") or raw.startswith("https://"):
                add_origin(raw)
            else:
                add_origin(f"https://{raw}")
                low = raw.lower()
                if low.startswith("www."):
                    add_origin(f"https://{raw[4:]}")
                else:
                    add_origin(f"https://www.{raw}")

        object.__setattr__(self, "cors_origins", origins)

    class Config:
        env_file = ".env"


settings = Settings()
