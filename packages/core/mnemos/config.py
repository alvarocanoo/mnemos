from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MNEMOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://mnemos:mnemos@localhost:5432/mnemos",
        description="SQLAlchemy URL for Postgres (use psycopg3 driver).",
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant HTTP endpoint.",
    )
    qdrant_collection: str = Field(
        default="mnemos",
        description="Qdrant collection name. Versioned per run during eval.",
    )
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="fastembed-compatible dense model id. bge-small-en-v1.5 for fast mode.",
    )
    embedding_dim: int = Field(
        default=1024,
        description="Dense embedding dimension. Must match model. BGE-M3=1024, bge-small=384.",
    )
    sparse_model: str = Field(
        default="Qdrant/bm25",
        description="fastembed-compatible sparse model id. v0.5 uses BM25.",
    )
    rrf_prefetch_limit: int = Field(
        default=50,
        description="How many candidates each retriever returns before RRF fusion.",
    )
    judge_model: str = Field(
        default="claude-haiku-4-5",
        description="LLM judge for contradiction eval (used in v0.5+).",
    )


def get_settings() -> Settings:
    return Settings()
