"""Mimesis Agent Service - FastAPI Application Entry Point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import MimesisError, mimesis_error_handler, unhandled_error_handler
from app.core.logging import (
    configure_logging,
    generate_request_id,
    get_logger,
    request_id_var,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "mimesis_starting",
        env=settings.app_env,
        project=settings.google_cloud_project,
    )
    yield
    logger.info("mimesis_shutting_down")


app = FastAPI(
    title="Mimesis",
    description="Agentic AI Creative Director for Short-Form Video Content",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001"
]

if settings.frontend_url:
    clean_frontend = settings.frontend_url.rstrip("/")
    if clean_frontend not in allowed_origins:
        allowed_origins.append(clean_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
app.add_exception_handler(MimesisError, mimesis_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Inject request correlation ID into every request."""
    rid = request.headers.get("X-Request-ID", generate_request_id())
    request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# Register routes
app.include_router(router)


# Health check
@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "mimesis-agent"}
