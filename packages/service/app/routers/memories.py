from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from mnemos.config import Settings
from mnemos.embeddings.bge_m3 import DenseEmbedder
from mnemos.memory.ops import (
    delete_memory,
    list_memories,
    read_memory_by_id,
    write_memory,
)
from mnemos.models import Memory, MemoryWrite
from mnemos.storage.qdrant import delete_point

from app.deps import EmbedderDep, SessionDep, SettingsDep

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=Memory, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryWrite,
    session: Session = SessionDep,
    embedder: DenseEmbedder = EmbedderDep,
    settings: Settings = SettingsDep,
) -> Memory:
    return write_memory(session, embedder, settings, payload)


@router.get("/{memory_id}", response_model=Memory)
def get_memory(memory_id: UUID, session: Session = SessionDep) -> Memory:
    memory = read_memory_by_id(session, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return memory


@router.get("", response_model=list[Memory])
def list_(
    session: Session = SessionDep,
    user_id: str = "default",
    limit: int = 100,
) -> list[Memory]:
    return list_memories(session, user_id=user_id, limit=limit)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    memory_id: UUID,
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
) -> None:
    if not delete_memory(session, memory_id):
        raise HTTPException(status_code=404, detail="memory not found")
    delete_point(settings, memory_id)
