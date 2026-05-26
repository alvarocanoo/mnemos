from fastapi import APIRouter
from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.models import SearchHit, SearchQuery
from mnemos.retrieval.dense import dense_search

from app.deps import EmbedderDep, SessionDep, SettingsDep

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/dense", response_model=list[SearchHit])
def search_dense_endpoint(
    payload: SearchQuery,
    session: Session = SessionDep,
    embedder: DenseEmbedder = EmbedderDep,
    settings: Settings = SettingsDep,
) -> list[SearchHit]:
    return dense_search(
        session=session,
        embedder=embedder,
        settings=settings,
        query=payload.query,
        user_id=payload.user_id,
        limit=payload.limit,
    )
