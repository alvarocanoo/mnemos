from collections.abc import Generator
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, create_engine, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from mnemos.config import Settings


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB}


class MemoryRow(Base):
    __tablename__ = "memories"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    content: Mapped[str] = mapped_column(String, nullable=False)
    importance: Mapped[int] = mapped_column(nullable=False, default=2)
    extra: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    access_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_memories_user_id", "user_id"),
        Index("ix_memories_created_at", "created_at"),
    )


_engine = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(settings: Settings) -> None:
    global _engine, _session_factory
    _engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    _session_factory = sessionmaker(_engine, expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("init_engine() must be called before get_session()")
    with _session_factory() as session:
        yield session


def session_scope() -> Session:
    if _session_factory is None:
        raise RuntimeError("init_engine() must be called before session_scope()")
    return _session_factory()
