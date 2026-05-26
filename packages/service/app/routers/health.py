from fastapi import APIRouter, Depends
from mnemos.config import Settings, get_settings
from mnemos.storage.qdrant import get_client
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import SessionDep

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(
    session: Session = SessionDep,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    pg_ok = False
    qd_ok = False
    pg_error: str | None = None
    qd_error: str | None = None

    try:
        session.execute(text("SELECT 1"))
        pg_ok = True
    except Exception as exc:
        pg_error = str(exc)

    try:
        get_client().get_collections()
        qd_ok = True
    except Exception as exc:
        qd_error = str(exc)

    return {
        "postgres": {"ok": pg_ok, "error": pg_error},
        "qdrant": {"ok": qd_ok, "error": qd_error},
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
    }
