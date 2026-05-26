from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from mnemos.config import Settings, get_settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.storage.postgres import get_session as _get_session


@lru_cache(maxsize=1)
def _embedder_singleton(model_name: str) -> DenseEmbedder:
    return DenseEmbedder(model_name=model_name)


def db_session() -> Generator[Session, None, None]:
    yield from _get_session()


def embedder(settings: Settings = Depends(get_settings)) -> DenseEmbedder:
    return _embedder_singleton(settings.embedding_model)


SettingsDep = Depends(get_settings)
SessionDep = Depends(db_session)
EmbedderDep = Depends(embedder)
