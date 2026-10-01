from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.exceptions import register_exception_handlers
from app.middleware import RequestContextMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse to serve production traffic on the public placeholder key. It signs
    # every session and every emailed action link, and the tenant id travels inside
    # those tokens, so a known key would let anyone mint access to any company.
    if settings.is_production and settings.uses_weak_jwt_secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is the default placeholder or shorter than 32 characters. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    # Startup: Start APScheduler
    start_scheduler()
    yield
    # Shutdown: Stop APScheduler
    shutdown_scheduler()


app = FastAPI(
    title="Sentinel API",
    description="Operational layer for a business: captures decisions, tracks who owes what, chases until done.",
    version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe. Does not touch the database."""
    return {"status": "ok", "environment": settings.environment}
