"""
app/api/health.py — Health Check Router
NEUM LEX COUNSEL

Endpoints:
  GET /health          Comprehensive health check (DB + Redis + Celery + S3)
  GET /health/live     Kubernetes liveness probe (just returns 200)
  GET /health/ready    Kubernetes readiness probe (checks DB + Redis)

Used by:
  - Docker HEALTHCHECK
  - Load balancer health probe
  - Kubernetes liveness/readiness probes
  - Celery worker health check endpoint
  - Admin dashboard worker health panel
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter()


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class ComponentHealth(BaseModel):
    status: str          # "ok" | "error" | "degraded"
    response_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str          # "healthy" | "degraded" | "unhealthy"
    version: str
    environment: str
    timestamp: str
    uptime_check: bool
    components: dict


# ---------------------------------------------------------------------------
# Component checks
# ---------------------------------------------------------------------------

async def _check_database() -> ComponentHealth:
    """Verify DB connection via SELECT 1. Measures response time."""
    start = time.perf_counter()
    try:
        from app.models.database import engine
        import sqlalchemy
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        ms = round((time.perf_counter() - start) * 1000, 2)
        status_str = "ok" if ms < 500 else "degraded"
        return ComponentHealth(status=status_str, response_ms=ms)
    except Exception as e:
        ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(status="error", response_ms=ms, detail=str(e)[:100])


async def _check_redis() -> ComponentHealth:
    """Verify Redis connection via PING. Measures response time."""
    start = time.perf_counter()
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await r.ping()
        await r.aclose()
        ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(status="ok", response_ms=ms)
    except Exception as e:
        ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(status="error", response_ms=ms, detail=str(e)[:100])


def _check_celery_workers() -> ComponentHealth:
    """Check if any Celery workers are active by pinging the broker."""
    start = time.perf_counter()
    try:
        from app.worker.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=3.0)
        active = inspector.active()
        ms = round((time.perf_counter() - start) * 1000, 2)
        if active is None:
            return ComponentHealth(
                status="degraded",
                response_ms=ms,
                detail="No workers responded to ping. Scheduled tasks may be delayed.",
            )
        worker_count = len(active)
        return ComponentHealth(
            status="ok",
            response_ms=ms,
            detail=f"{worker_count} worker(s) active",
        )
    except Exception as e:
        ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(
            status="error",
            response_ms=ms,
            detail=str(e)[:100],
        )


async def _check_s3() -> ComponentHealth:
    """Verify S3 bucket is accessible (head_bucket). Only runs if AWS is configured."""
    if not settings.aws_s3_bucket:
        return ComponentHealth(status="ok", detail="S3 not configured — skipped")

    start = time.perf_counter()
    try:
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        s3.head_bucket(Bucket=settings.aws_s3_bucket)
        ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(status="ok", response_ms=ms)
    except Exception as e:
        ms = round((time.perf_counter() - start) * 1000, 2)
        return ComponentHealth(status="error", response_ms=ms, detail=str(e)[:100])


# ---------------------------------------------------------------------------
# GET /health — Full health check
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary="Full system health check",
    description="Checks DB, Redis, Celery workers, and S3. Returns overall status.",
    tags=["Health"],
)
async def full_health_check():
    """
    Returns 200 if healthy or degraded.
    Returns 503 if any critical component (DB or Redis) is unavailable.
    """
    # Run all checks
    db_health = await _check_database()
    redis_health = await _check_redis()
    celery_health = _check_celery_workers()
    s3_health = await _check_s3()

    components = {
        "database": db_health.model_dump(),
        "redis": redis_health.model_dump(),
        "celery_workers": celery_health.model_dump(),
        "s3": s3_health.model_dump(),
    }

    # Determine overall status
    critical_ok = (
        db_health.status == "ok"
        and redis_health.status in ("ok", "degraded")
    )
    has_degraded = any(
        c["status"] == "degraded" for c in components.values()
    )
    has_error = any(
        c["status"] == "error" for c in components.values()
    )

    if not critical_ok:
        overall = "unhealthy"
    elif has_error or has_degraded:
        overall = "degraded"
    else:
        overall = "healthy"

    response_body = {
        "status": overall,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_check": True,
        "components": components,
    }

    http_status = (
        status.HTTP_200_OK
        if overall in ("healthy", "degraded")
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    if overall != "healthy":
        logger.warning(
            "health_check_not_healthy",
            overall=overall,
            db=db_health.status,
            redis=redis_health.status,
            celery=celery_health.status,
        )

    return JSONResponse(content=response_body, status_code=http_status)


# ---------------------------------------------------------------------------
# GET /health/live — Kubernetes liveness probe
# ---------------------------------------------------------------------------

@router.get(
    "/health/live",
    summary="Liveness probe — confirms the process is running",
    tags=["Health"],
)
async def liveness():
    """
    Returns 200 immediately. Used by Kubernetes to determine if the container
    should be restarted. If this fails, the process is deadlocked/crashed.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /health/ready — Kubernetes readiness probe
# ---------------------------------------------------------------------------

@router.get(
    "/health/ready",
    summary="Readiness probe — confirms the app is ready to serve traffic",
    tags=["Health"],
)
async def readiness():
    """
    Checks DB and Redis. Returns 200 only if both are reachable.
    Used by Kubernetes to route traffic only to ready pods.
    Used by Docker Swarm / load balancer for routing.
    """
    db_health = await _check_database()
    redis_health = await _check_redis()

    ready = (
        db_health.status == "ok"
        and redis_health.status in ("ok", "degraded")
    )

    response = {
        "ready": ready,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_health.status,
        "redis": redis_health.status,
    }

    return JSONResponse(
        content=response,
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
