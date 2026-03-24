from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import settings
from routers import health, signals, price_updates, stats, export

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

@app.get("/")
async def root():
    return {"message": "VNINDEX Signal API", "docs": "/docs"}
