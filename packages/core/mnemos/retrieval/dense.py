from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.memory.ops import row_to_model
from mnemos.models import SearchHit
from mnemos.storage.postgres import MemoryRow
from mnemos.storage.qdrant import search_dense


def dense_search(
    session: Session,
    embedder: DenseEmbedder,
    settings: Settings,
    query: str,
    user_id: str = "default",
    limit: int = 10,
) -> list[SearchHit]:
    query_vector = embedder.embed_one(query)
    hits = search_dense(settings, query_vector, user_id=user_id, limit=limit)
    if not hits:
        return []

    id_to_score = {memory_id: score for memory_id, score in hits}
    rows = (
        session.query(MemoryRow)
        .filter(MemoryRow.id.in_(id_to_score.keys()))
        .all()
    )
    results = [
        SearchHit(memory=row_to_model(row), score=id_to_score[row.id])
        for row in rows
    ]
    results.sort(key=lambda h: h.score, reverse=True)
    return results
