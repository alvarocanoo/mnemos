from collections.abc import Iterable
from dataclasses import dataclass

from fastembed import SparseTextEmbedding


@dataclass
class SparseVec:
    """Sparse vector in Qdrant-compatible shape."""

    indices: list[int]
    values: list[float]


class SparseEmbedder:
    """Lazy-loaded fastembed wrapper for BM25-style sparse embeddings.

    BM25 stats (idf, avgdl) are estimated by fastembed against its built-in
    background corpus; v0.5 does not refit them on mnemos memories. v1.0
    can revisit if recall degrades on domain-shifted datasets.
    """

    def __init__(self, model_name: str = "Qdrant/bm25") -> None:
        self.model_name = model_name
        self._model: SparseTextEmbedding | None = None

    def _ensure_loaded(self) -> SparseTextEmbedding:
        if self._model is None:
            self._model = SparseTextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, texts: Iterable[str]) -> list[SparseVec]:
        model = self._ensure_loaded()
        return [
            SparseVec(indices=list(vec.indices.tolist()), values=list(vec.values.tolist()))
            for vec in model.embed(list(texts))
        ]

    def embed_one(self, text: str) -> SparseVec:
        return self.embed([text])[0]
