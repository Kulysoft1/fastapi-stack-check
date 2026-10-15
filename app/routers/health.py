# app/routers/health.py
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app import redis_client as rc
from app.schemas import HealthReadyResponse, HealthResponse, ServiceHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check - always returns ok if app is running."""
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthReadyResponse)
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> HealthReadyResponse:
    """Readiness check - verifies both Postgres and Redis are accessible.

    Returns 503 with per-service details when either store is unavailable.
    """
    services: list[ServiceHealth] = []
    overall_ok = True

    # Check PostgreSQL
    pg_start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        pg_latency = int((time.perf_counter() - pg_start) * 1000)
        services.append(ServiceHealth(service="postgres", status="ok", latency_ms=pg_latency))
    except Exception as e:
        pg_latency = int((time.perf_counter() - pg_start) * 1000)
        services.append(
            ServiceHealth(service="postgres", status="down", latency_ms=pg_latency, error=str(e))
        )
        overall_ok = False

    # Check Redis
    redis_start = time.perf_counter()
    try:
        client = rc._redis_client
        if client is None:
            raise RuntimeError("Redis client not initialized")
        await client.ping()
        redis_latency = int((time.perf_counter() - redis_start) * 1000)
        services.append(ServiceHealth(service="redis", status="ok", latency_ms=redis_latency))
    except Exception as e:
        redis_latency = int((time.perf_counter() - redis_start) * 1000)
        services.append(
            ServiceHealth(service="redis", status="down", latency_ms=redis_latency, error=str(e))
        )
        overall_ok = False

    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthReadyResponse(
        status="ok" if overall_ok else "degraded",
        services=services,
    )
