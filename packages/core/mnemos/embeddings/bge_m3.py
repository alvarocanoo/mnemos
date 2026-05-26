from collections.abc import Iterable

from fastembed import TextEmbedding


class DenseEmbedder:
    """Lazy-loaded fastembed wrapper for dense embeddings.

    Why lazy: the BGE-M3 model is ~2GB; we only want to pay that cost when
    embedding is actually called, not on module import (e.g. during alembic
    migrations or HTTP healthchecks).
    """

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self.model_name = model_name
        self._model: TextEmbedding | None = None

    def _ensure_loaded(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        model = self._ensure_loaded()
        return [vec.tolist() for vec in model.embed(list(texts))]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
