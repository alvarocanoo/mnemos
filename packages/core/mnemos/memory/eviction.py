from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemos.memory.decay import DecayConfig, age_in_days, decay_weight
from mnemos.storage.postgres import MemoryRow


@dataclass(frozen=True)
class EvictionConfig:
    """Weights for the composite eviction score.

    Final score = w_importance * importance
                 + w_recency    * decay_weight(age)
                 + w_access     * log(1 + access_count)

    Higher score = more valuable, less likely to be evicted.
    Defaults treat importance and recency as equally weighted, with
    access frequency as a smaller boost. Tunable via Settings.eviction_*.
    """

    w_importance: float = 1.0
    w_recency: float = 1.0
    w_access: float = 0.5


@dataclass(frozen=True)
class ScoredMemory:
    memory_id: UUID
    importance: int
    age_days: float
    access_count: int
    recency_weight: float
    score: float


def composite_score(
    importance: int,
    recency_weight: float,
    access_count: int,
    cfg: EvictionConfig | None = None,
) -> float:
    c = cfg or EvictionConfig()
    return (
        c.w_importance * float(importance)
        + c.w_recency * float(recency_weight)
        + c.w_access * math.log1p(max(0, access_count))
    )


def score_user_memories(
    session: Session,
    user_id: str,
    *,
    decay_cfg: DecayConfig | None = None,
    eviction_cfg: EvictionConfig | None = None,
    now: datetime | None = None,
) -> list[ScoredMemory]:
    """Score every memory of a user. Cheap for the v0.5 scale (<10k memories per user)."""
    dcfg = decay_cfg or DecayConfig()
    ecfg = eviction_cfg or EvictionConfig()
    rows = session.execute(select(MemoryRow).where(MemoryRow.user_id == user_id)).scalars().all()

    scored: list[ScoredMemory] = []
    for row in rows:
        age = age_in_days(row.created_at, now=now)
        recency = decay_weight(row.importance, age, dcfg)
        score = composite_score(row.importance, recency, row.access_count, ecfg)
        scored.append(
            ScoredMemory(
                memory_id=row.id,
                importance=row.importance,
                age_days=age,
                access_count=row.access_count,
                recency_weight=recency,
                score=score,
            )
        )
    scored.sort(key=lambda s: s.score)
    return scored


def select_for_eviction(
    session: Session,
    user_id: str,
    max_count: int,
    *,
    decay_cfg: DecayConfig | None = None,
    eviction_cfg: EvictionConfig | None = None,
    now: datetime | None = None,
) -> list[ScoredMemory]:
    """If the user has more than max_count memories, return the lowest-scored excess.

    Returns an empty list when the user is under cap.
    """
    if max_count < 0:
        raise ValueError("max_count must be >= 0")
    scored = score_user_memories(
        session,
        user_id,
        decay_cfg=decay_cfg,
        eviction_cfg=eviction_cfg,
        now=now,
    )
    excess = len(scored) - max_count
    if excess <= 0:
        return []
    return scored[:excess]
