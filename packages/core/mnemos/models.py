from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryWrite(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)
    importance: int = Field(default=2, ge=1, le=3, description="1=low, 2=normal, 3=high")
    user_id: str = Field(default="default", max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Memory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    importance: int
    user_id: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    access_count: int
    last_accessed_at: datetime | None


class SearchHit(BaseModel):
    memory: Memory
    score: float


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="default", max_length=128)
    limit: int = Field(default=10, ge=1, le=100)
