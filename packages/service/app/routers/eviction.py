from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.memory.decay import DecayConfig
from mnemos.memory.eviction import (
    EvictionConfig,
    score_user_memories,
    select_for_eviction,
)
from mnemos.storage.postgres import MemoryRow
from mnemos.storage.qdrant import delete_points_bulk

from app.deps import SessionDep, SettingsDep

router = APIRouter(prefix="/memories", tags=["eviction"])


class EvictionRequest(BaseModel):
    user_id: str = Field(default="default", max_length=128)
    max_count: int = Field(..., ge=0, description="Cap on memories to keep for this user.")


class ScoreItem(BaseModel):
    memory_id: UUID
    importance: int
    age_days: float
    access_count: int
    recency_weight: float
    score: float


class EvictionResponse(BaseModel):
    evicted: list[UUID]
    remaining: int


def _decay(settings: Settings) -> DecayConfig:
    return DecayConfig(
        lambda_low=settings.decay_lambda_low,
        lambda_normal=settings.decay_lambda_normal,
        lambda_high=settings.decay_lambda_high,
    )


def _evict_cfg(settings: Settings) -> EvictionConfig:
    return EvictionConfig(
        w_importance=settings.eviction_w_importance,
        w_recency=settings.eviction_w_recency,
        w_access=settings.eviction_w_access,
    )


@router.post("/score-eviction", response_model=list[ScoreItem])
def score_eviction(
    user_id: str = "default",
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
) -> list[ScoreItem]:
    """Dry-run: return every memory's composite score, ascending. No deletes."""
    scored = score_user_memories(
        session, user_id, decay_cfg=_decay(settings), eviction_cfg=_evict_cfg(settings)
    )
    return [
        ScoreItem(
            memory_id=s.memory_id,
            importance=s.importance,
            age_days=round(s.age_days, 2),
            access_count=s.access_count,
            recency_weight=round(s.recency_weight, 4),
            score=round(s.score, 4),
        )
        for s in scored
    ]


@router.post("/evict", response_model=EvictionResponse)
def evict(
    payload: EvictionRequest,
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
) -> EvictionResponse:
    """Drop the lowest-scored memories until at most max_count remain.

    Idempotent: calling again with the same max_count when the user is
    already under cap returns an empty evicted list. Deletes are
    transactional in Postgres; Qdrant points are removed in a bulk call
    after the SQL commit so a Postgres failure cannot orphan vectors.
    """
    targets = select_for_eviction(
        session, payload.user_id, payload.max_count,
        decay_cfg=_decay(settings), eviction_cfg=_evict_cfg(settings),
    )
    if not targets:
        remaining = session.query(MemoryRow).filter(
            MemoryRow.user_id == payload.user_id
        ).count()
        return EvictionResponse(evicted=[], remaining=remaining)

    ids = [t.memory_id for t in targets]
    session.query(MemoryRow).filter(MemoryRow.id.in_(ids)).delete(
        synchronize_session=False
    )
    session.commit()

    delete_points_bulk(settings, ids)

    remaining = session.query(MemoryRow).filter(
        MemoryRow.user_id == payload.user_id
    ).count()
    return EvictionResponse(evicted=ids, remaining=remaining)
