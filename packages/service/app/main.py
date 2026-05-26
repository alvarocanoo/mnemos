from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from mnemos.config import get_settings
from mnemos.storage.postgres import init_engine
from mnemos.storage.qdrant import ensure_collection, init_client

from app.routers import contradiction, eviction, health, memories, search

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_engine(settings)
    init_client(settings)
    ensure_collection(settings)
    log.info(
        "mnemos.service.started",
        qdrant_collection=settings.qdrant_collection,
        embedding_model=settings.embedding_model,
    )
    yield
    log.info("mnemos.service.stopped")


app = FastAPI(title="mnemos", version="0.0.1", lifespan=lifespan)

app.include_router(health.router)
app.include_router(memories.router)
app.include_router(eviction.router)
app.include_router(search.router)
app.include_router(contradiction.router)
