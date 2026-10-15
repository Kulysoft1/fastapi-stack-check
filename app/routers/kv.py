# app/routers/kv.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.redis_client import get_redis
from app.schemas import KVListResponse, KVResponse, KVSetRequest

router = APIRouter(prefix="/api/kv", tags=["kv"])


@router.get("", response_model=KVListResponse)
async def list_keys(
    redis: Annotated[Redis, Depends(get_redis)],
) -> KVListResponse:
    """List all keys with values and TTL using SCAN."""
    try:
        keys_data: list[KVResponse] = []
        cursor = 0

        while True:
            cursor, keys = await redis.scan(cursor=cursor, count=100)
            if keys:
                # Get values directly
                values = await redis.mget(keys)

                # Get TTLs in pipeline
                pipe = redis.pipeline()
                for key in keys:
                    pipe.ttl(key)
                ttls = await pipe.execute()

                for key, value, ttl in zip(keys, values, ttls):
                    if value is not None:
                        keys_data.append(
                            KVResponse(
                                key=key,
                                value=value,
                                ttl=ttl if ttl > 0 else None,
                            )
                        )

            if cursor == 0:
                break

        return KVListResponse(keys=keys_data)
    except RedisError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Redis unavailable", "detail": str(e)},
        )


@router.put("/{key}", response_model=KVResponse)
async def set_key(
    key: str,
    request: KVSetRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> KVResponse:
    """Set a key with optional TTL."""
    try:
        if request.ttl is not None:
            await redis.setex(key, request.ttl, request.value)
            ttl = request.ttl
        else:
            await redis.set(key, request.value)
            ttl = None

        return KVResponse(key=key, value=request.value, ttl=ttl)
    except RedisError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Redis unavailable", "detail": str(e)},
        )


@router.get("/{key}", response_model=KVResponse)
async def get_key(
    key: str,
    redis: Annotated[Redis, Depends(get_redis)],
) -> KVResponse:
    """Get a key's value and remaining TTL."""
    try:
        pipe = redis.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        value, ttl = await pipe.execute()

        if value is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

        return KVResponse(key=key, value=value, ttl=ttl if ttl > 0 else None)
    except RedisError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Redis unavailable", "detail": str(e)},
        )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key: str,
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    """Delete a key."""
    try:
        deleted = await redis.delete(key)
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    except RedisError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Redis unavailable", "detail": str(e)},
        )