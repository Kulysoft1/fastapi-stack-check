# app/schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# Note schemas
class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)


class NoteCreate(NoteBase):
    pass


class NoteResponse(NoteBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# KV schemas
class KVSetRequest(BaseModel):
    value: str
    ttl: Optional[int] = Field(default=None, ge=1, description="TTL in seconds")


class KVResponse(BaseModel):
    key: str
    value: str
    ttl: Optional[int] = None  # Remaining TTL in seconds, None if no expiry


class KVListResponse(BaseModel):
    keys: list[KVResponse]


# Health schemas
class ServiceHealth(BaseModel):
    service: str
    status: str  # "ok" | "down"
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class HealthReadyResponse(BaseModel):
    status: str  # "ok" | "degraded"
    services: list[ServiceHealth]


class HealthResponse(BaseModel):
    status: str = "ok"