from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Mahakosh"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars",
        min_length=32,
    )

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    DATABASE_URL: str = "postgresql+asyncpg://mahakosh:mahakosh_secret@localhost:5432/mahakosh"
    DATABASE_SYNC_URL: str = "postgresql://mahakosh:mahakosh_secret@localhost:5432/mahakosh"

    REDIS_URL: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "mahakosh_minio"
    MINIO_SECRET_KEY: str = "mahakosh_minio_secret"
    MINIO_BUCKET: str = "mahakosh-documents"
    MINIO_USE_SSL: bool = False

    TEMPORAL_HOST: str = "localhost"
    TEMPORAL_PORT: int = 7233
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "mahakosh-workflows"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2"

    # Knowledge / Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_FALLBACK_MODEL: str = "nomic-embed-text"
    RERANKER_MODEL: str = "BAAI/bge-reranker-large"
    EMBEDDING_DIMENSION: int = 1024
    CHUNK_SIZE_TOKENS: int = 1000
    CHUNK_OVERLAP_TOKENS: int = 150
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 5
    QDRANT_COLLECTION_PREFIX: str = "mahakosh"

    JWT_SECRET_KEY: str = Field(
        default="dev-jwt-secret-key-change-in-production-min-32",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def temporal_address(self) -> str:
        return f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}"

    @field_validator("DATABASE_URL", "DATABASE_SYNC_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("Database URL is required")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
