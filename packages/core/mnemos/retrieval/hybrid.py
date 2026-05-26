from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.embeddings.bm25 import SparseEmbedder
from mnemos.memory.ops import row_to_model
from mnemos.models import SearchHit
from mnemos.storage.postgres import MemoryRow
from mnemos.storage.qdrant import hybrid_search as hybrid_query


def hybrid_search(
    session: Session,
    dense_embedder: DenseEmbedder,
    sparse_embedder: SparseEmbedder,
    settings: Settings,
    query: str,
    user_id: str = "default",
    limit: int = 10,
    prefetch_limit: int = 50,
) -> list[SearchHit]:
    dense_vec = dense_embedder.embed_one(query)
    sparse_vec = sparse_embedder.embed_one(query)

    hits = hybrid_query(
        settings,
        dense_query=dense_vec,
        sparse_query=sparse_vec,
        user_id=user_id,
        limit=limit,
        prefetch_limit=prefetch_limit,
    )
    if not hits:
        return []

    id_to_score = {memory_id: score for memory_id, score in hits}
    rows = (
        session.query(MemoryRow)
        .filter(MemoryRow.id.in_(id_to_score.keys()))
        .all()
    )
    results = [
        SearchHit(memory=row_to_model(row), score=id_to_score[row.id]) for row in rows
    ]
    results.sort(key=lambda h: h.score, reverse=True)
    return results
