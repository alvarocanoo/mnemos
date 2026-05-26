from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.embeddings.bm25 import SparseEmbedder
from mnemos.models import Memory, MemoryWrite
from mnemos.storage.postgres import MemoryRow
from mnemos.storage.qdrant import upsert_point


def row_to_model(row: MemoryRow) -> Memory:
    return Memory(
        id=row.id,
        content=row.content,
        importance=row.importance,
        user_id=row.user_id,
        metadata=row.extra,
        created_at=row.created_at,
        updated_at=row.updated_at,
        access_count=row.access_count,
        last_accessed_at=row.last_accessed_at,
    )


def write_memory(
    session: Session,
    dense_embedder: DenseEmbedder,
    sparse_embedder: SparseEmbedder,
    settings: Settings,
    payload: MemoryWrite,
) -> Memory:
    row_kwargs: dict = {
        "content": payload.content,
        "importance": payload.importance,
        "user_id": payload.user_id,
        "extra": payload.metadata,
    }
    if payload.created_at is not None:
        row_kwargs["created_at"] = payload.created_at
        row_kwargs["updated_at"] = payload.created_at
    row = MemoryRow(**row_kwargs)
    session.add(row)
    session.commit()
    session.refresh(row)

    dense_vec = dense_embedder.embed_one(payload.content)
    sparse_vec = sparse_embedder.embed_one(payload.content)
    upsert_point(
        settings,
        row.id,
        dense=dense_vec,
        sparse=sparse_vec,
        payload={"user_id": row.user_id, "importance": row.importance},
    )

    return row_to_model(row)


def read_memory_by_id(
    session: Session, memory_id: UUID, *, bump_access: bool = True
) -> Memory | None:
    row = session.get(MemoryRow, memory_id)
    if row is None:
        return None
    if bump_access:
        row.access_count += 1
        row.last_accessed_at = datetime.now(UTC)
        session.commit()
        session.refresh(row)
    return row_to_model(row)


def list_memories(session: Session, user_id: str = "default", limit: int = 100) -> list[Memory]:
    stmt = (
        select(MemoryRow)
        .where(MemoryRow.user_id == user_id)
        .order_by(MemoryRow.created_at.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()
    return [row_to_model(r) for r in rows]


def delete_memory(session: Session, memory_id: UUID) -> bool:
    row = session.get(MemoryRow, memory_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
