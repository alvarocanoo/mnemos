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
        description="LLM judge for contradiction detection (Anthropic API).",
    )
    judge_max_tokens: int = Field(
        default=256,
        description="Cap on judge response length (tool_use output is tiny).",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.",
    )
    nli_model: str = Field(
        default="cross-encoder/nli-deberta-v3-base",
        description="HF model id for the NLI baseline judge.",
    )
    nli_threshold: float = Field(
        default=0.5,
        description="Probability threshold for the NLI baseline verdicts.",
    )

    apply_decay: bool = Field(
        default=True,
        description="Multiply retrieval scores by exp(-λ_i · Δt) before final ranking.",
    )
    decay_lambda_low: float = Field(default=0.05, description="λ for importance=1 memories.")
    decay_lambda_normal: float = Field(default=0.02, description="λ for importance=2 memories.")
    decay_lambda_high: float = Field(default=0.005, description="λ for importance=3 memories.")

    eviction_w_importance: float = Field(
        default=1.0, description="Eviction composite weight for importance."
    )
    eviction_w_recency: float = Field(
        default=1.0, description="Eviction composite weight for recency (decay weight)."
    )
    eviction_w_access: float = Field(
        default=0.5, description="Eviction composite weight for log(1+access_count)."
    )


def get_settings() -> Settings:
    return Settings()
