from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.memory.decay import DecayConfig, age_in_days, decay_weight
from mnemos.memory.ops import row_to_model
from mnemos.models import SearchHit
from mnemos.storage.postgres import MemoryRow
from mnemos.storage.qdrant import search_dense as qdrant_dense


def _decay_cfg(settings: Settings) -> DecayConfig:
    return DecayConfig(
        lambda_low=settings.decay_lambda_low,
        lambda_normal=settings.decay_lambda_normal,
        lambda_high=settings.decay_lambda_high,
    )


def dense_search(
    session: Session,
    embedder: DenseEmbedder,
    settings: Settings,
    query: str,
    user_id: str = "default",
    limit: int = 10,
    apply_decay: bool | None = None,
    score_threshold: float | None = None,
) -> list[SearchHit]:
    query_vector = embedder.embed_one(query)
    apply = settings.apply_decay if apply_decay is None else apply_decay
    overfetch = limit * 3 if apply else limit
    hits = qdrant_dense(settings, query_vector, user_id=user_id, limit=overfetch)
    if not hits:
        return []

    id_to_score = dict(hits)
    rows = session.query(MemoryRow).filter(MemoryRow.id.in_(id_to_score.keys())).all()

    cfg = _decay_cfg(settings) if apply else None
    results: list[SearchHit] = []
    for row in rows:
        score = id_to_score[row.id]
        if apply and cfg is not None:
            score *= decay_weight(row.importance, age_in_days(row.created_at), cfg)
        results.append(SearchHit(memory=row_to_model(row), score=score))
    results.sort(key=lambda h: h.score, reverse=True)
    if score_threshold is not None:
        results = [h for h in results if h.score >= score_threshold]
    return results[:limit]
