from fastapi import APIRouter
from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.embeddings.bm25 import SparseEmbedder
from mnemos.models import SearchHit, SearchQuery
from mnemos.retrieval.dense import dense_search
from mnemos.retrieval.hybrid import hybrid_search

from app.deps import (
    DenseEmbedderDep,
    SessionDep,
    SettingsDep,
    SparseEmbedderDep,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/dense", response_model=list[SearchHit])
def search_dense_endpoint(
    payload: SearchQuery,
    session: Session = SessionDep,
    dense: DenseEmbedder = DenseEmbedderDep,
    settings: Settings = SettingsDep,
) -> list[SearchHit]:
    return dense_search(
        session=session,
        embedder=dense,
        settings=settings,
        query=payload.query,
        user_id=payload.user_id,
        limit=payload.limit,
    )


@router.post("/hybrid", response_model=list[SearchHit])
def search_hybrid_endpoint(
    payload: SearchQuery,
    session: Session = SessionDep,
    dense: DenseEmbedder = DenseEmbedderDep,
    sparse: SparseEmbedder = SparseEmbedderDep,
    settings: Settings = SettingsDep,
) -> list[SearchHit]:
    return hybrid_search(
        session=session,
        dense_embedder=dense,
        sparse_embedder=sparse,
        settings=settings,
        query=payload.query,
        user_id=payload.user_id,
        limit=payload.limit,
        prefetch_limit=settings.rrf_prefetch_limit,
    )
