# app/redis_client.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import HTTPException, status
import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

_redis_client: Optional[Redis] = None


async def init_redis() -> Optional[Redis]:
    """Initialize Redis connection pool. Returns None if connection fails."""
    global _redis_client
    try:
        _redis_client = redis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
        )
        # Test connection
        await _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def get_redis() -> Redis:
    """Get the Redis client (must be initialized first)."""
    if _redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Redis unavailable", "detail": "Redis client not initialized"},
        )
    return _redis_client


@asynccontextmanager
async def get_redis_context() -> AsyncGenerator[Redis, None]:
    """Context manager for Redis client."""
    client = get_redis()
    try:
        yield client
    finally:
        pass  # Client is managed globally