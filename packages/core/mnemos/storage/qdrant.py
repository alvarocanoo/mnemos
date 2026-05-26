from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from mnemos.config import Settings


_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"


_client: QdrantClient | None = None


def init_client(settings: Settings) -> None:
    global _client
    _client = QdrantClient(url=settings.qdrant_url)


def get_client() -> QdrantClient:
    if _client is None:
        raise RuntimeError("init_client() must be called before get_client()")
    return _client


def ensure_collection(settings: Settings) -> None:
    """Create the collection if missing, with named dense + sparse slots.

    Sparse is created from day one (even though v0.1 doesn't write to it) so
    that v0.5 can add BM25 ingest without recreating the collection.
    """
    client = get_client()
    if client.collection_exists(settings.qdrant_collection):
        return

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            _DENSE_VECTOR_NAME: qm.VectorParams(
                size=settings.embedding_dim, distance=qm.Distance.COSINE
            ),
        },
        sparse_vectors_config={
            _SPARSE_VECTOR_NAME: qm.SparseVectorParams(
                index=qm.SparseIndexParams(on_disk=False),
            ),
        },
    )


def upsert_dense(
    settings: Settings, memory_id: UUID, vector: list[float], payload: dict
) -> None:
    client = get_client()
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qm.PointStruct(
                id=str(memory_id),
                vector={_DENSE_VECTOR_NAME: vector},
                payload=payload,
            )
        ],
    )


def search_dense(
    settings: Settings,
    query_vector: list[float],
    user_id: str,
    limit: int,
) -> list[tuple[UUID, float]]:
    client = get_client()
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        using=_DENSE_VECTOR_NAME,
        query_filter=qm.Filter(
            must=[qm.FieldCondition(key="user_id", match=qm.MatchValue(value=user_id))]
        ),
        limit=limit,
        with_payload=False,
    )
    return [(UUID(str(point.id)), float(point.score)) for point in response.points]


def delete_point(settings: Settings, memory_id: UUID) -> None:
    client = get_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qm.PointIdsList(points=[str(memory_id)]),
    )
