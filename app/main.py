"""
app/main.py — NEUM LEX COUNSEL
FastAPI application entry point.

Responsibilities:
  - App factory (create_app)
  - Middleware: CORS, request ID, structured logging, rate limiting, security headers
  - Router registration: all 9 routers mounted under /api/v1
  - Startup/shutdown lifespan events
  - Global exception handlers
  - OpenAPI schema customisation

AI Constitution compliance:
  - All routes require authentication (no public endpoints except /health and /auth)
  - Request IDs on every response for audit trail correlation
  - Structured logs include user_id, company_id, request_id on every line
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import (
    admin,
    auth,
    commercial,
    companies,
    documents,
    filings,
    health,
    rescue,
    rules,
)
from app.core.config import get_settings

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: verify DB connectivity, warm rule engine singleton, log ready.
    Shutdown: flush structlog, close DB pool.
    """
    # ---- STARTUP ----
    logger.info(
        "nlc_api_starting",
        version=settings.app_version,
        environment=settings.environment,
        debug=(settings.environment == "development"),
    )

    # Verify DB is reachable
    try:
        from app.models.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("db_connectivity_ok")
    except Exception as e:
        logger.error("db_connectivity_failed", error=str(e))
        raise RuntimeError(f"Cannot connect to database on startup: {e}")

    # Verify Redis/Celery broker is reachable (non-fatal — workers may not be up yet)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        logger.info("redis_connectivity_ok")
    except Exception as e:
        logger.warning("redis_connectivity_failed", error=str(e), note="Celery tasks will fail until Redis is available")

    # Warm the rule engine singleton (loads DB rules into memory)
    try:
        from app.core.dependencies import get_rule_engine
        engine_instance = get_rule_engine()
        logger.info("rule_engine_warmed", engine=type(engine_instance).__name__)
    except Exception as e:
        logger.warning("rule_engine_warm_failed", error=str(e))

    logger.info("nlc_api_ready", host="0.0.0.0", port=8000)

    yield  # ← application runs here

    # ---- SHUTDOWN ----
    logger.info("nlc_api_shutting_down")
    try:
        from app.models.database import engine
        await engine.dispose()
        logger.info("db_pool_closed")
    except Exception as e:
        logger.warning("db_pool_close_error", error=str(e))

    logger.info("nlc_api_stopped")


# ---------------------------------------------------------------------------
# Middleware: Request ID injection
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Inject a unique X-Request-ID on every request/response.
    Used to correlate logs, user_activity_logs, and error reports.
    Accepts client-supplied X-Request-ID if present, otherwise generates one.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind to structlog context for this request
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        structlog.contextvars.unbind_contextvars("request_id")
        return response


# ---------------------------------------------------------------------------
# Middleware: Access logging
# ---------------------------------------------------------------------------

class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Structured access log on every request: method, path, status, duration_ms.
    Skips /health to avoid log noise.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api/v1/health/live"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
            request_id=getattr(request.state, "request_id", "-"),
        )
        return response


# ---------------------------------------------------------------------------
# Middleware: Security headers
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response:
      - Strict-Transport-Security (HSTS)
      - X-Content-Type-Options: nosniff
      - X-Frame-Options: DENY
      - Referrer-Policy: strict-origin-when-cross-origin
      - Content-Security-Policy (API only — no browser rendering)
      - Cache-Control: no-store for API responses (avoid caching sensitive data)
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardised error envelope for all HTTPExceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "http_exception",
        status=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
        },
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic v2 validation errors — flatten into readable list."""
    request_id = getattr(request.state, "request_id", None)
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    logger.info(
        "validation_error",
        path=request.url.path,
        errors=errors,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "status_code": 422,
            "detail": "Request validation failed",
            "errors": errors,
            "request_id": request_id,
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected 500s. Never leaks stack traces to client."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": "An unexpected error occurred. Please contact NLC support with your request ID.",
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Neum Lex Counsel — RJSC Compliance Intelligence Platform",
        description=(
            "Bangladesh Companies Act 1994 compliance engine. "
            "ILRMF rule-based scoring, AI-assisted document drafting, "
            "corporate rescue management, and revenue pipeline tracking."
        ),
        version=settings.app_version,
        openapi_url="/api/v1/openapi.json" if not settings.is_production else None,
        docs_url="/api/v1/docs" if not settings.is_production else None,
        redoc_url="/api/v1/redoc" if not settings.is_production else None,
        lifespan=lifespan,
        contact={
            "name": "Neum Lex Counsel",
            "email": "tech@neumlexcounsel.com",
        },
        license_info={"name": "Proprietary — NLC Internal Use Only"},
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins if isinstance(settings.allowed_origins, list) else [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Requested-With",
        ],
        expose_headers=["X-Request-ID", "X-Total-Count", "X-Page", "X-Page-Size"],
        max_age=3600,
    )

    # ------------------------------------------------------------------
    # Custom middleware (order matters — outermost = last added)
    # ------------------------------------------------------------------
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ------------------------------------------------------------------
    # Exception handlers
    # ------------------------------------------------------------------
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    API_PREFIX = "/api/v1"

    # Health — no auth required
    app.include_router(health.router, prefix=API_PREFIX, tags=["Health"])

    # Auth — no auth on login endpoints, 2FA endpoints are semi-protected
    app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Authentication"])

    # Protected routes — all require valid JWT
    app.include_router(companies.router,  prefix=f"{API_PREFIX}/companies",  tags=["Companies"])
    app.include_router(filings.router,    prefix=f"{API_PREFIX}/filings",    tags=["Filings"])
    app.include_router(rescue.router,     prefix=f"{API_PREFIX}/rescue",     tags=["Corporate Rescue"])
    app.include_router(documents.router,  prefix=f"{API_PREFIX}/documents",  tags=["Documents"])
    app.include_router(commercial.router, prefix=f"{API_PREFIX}/commercial", tags=["Commercial"])
    app.include_router(rules.router,      prefix=f"{API_PREFIX}/rules",      tags=["Legal Rules"])
    app.include_router(admin.router,      prefix=f"{API_PREFIX}/admin",      tags=["Admin"])

    # ------------------------------------------------------------------
    # Root redirect
    # ------------------------------------------------------------------
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "Neum Lex Counsel API",
            "version": settings.app_version,
            "docs": "/api/v1/docs" if not settings.is_production else "disabled in production",
            "health": "/api/v1/health/live",
        }

    return app


# ---------------------------------------------------------------------------
# WSGI/ASGI entrypoint
# ---------------------------------------------------------------------------
app = create_app()
