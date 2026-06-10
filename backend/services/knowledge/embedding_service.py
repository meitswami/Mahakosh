import structlog
from typing import Any

from backend.core.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Generates embeddings using BAAI/bge-large-en-v1.5 with nomic-embed-text fallback."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._fallback_model = None
        self._dimension = settings.EMBEDDING_DIMENSION

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_primary(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("loading_embedding_model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def _load_fallback(self):
        if self._fallback_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("loading_fallback_embedding_model", model=settings.EMBEDDING_FALLBACK_MODEL)
                self._fallback_model = SentenceTransformer(settings.EMBEDDING_FALLBACK_MODEL)
            except Exception as exc:
                logger.warning("fallback_model_load_failed", error=str(exc))
        return self._fallback_model

    def embed_text(self, text: str, prefix: str = "") -> list[float]:
        full_text = f"{prefix}{text}" if prefix else text
        return self.embed_batch([full_text])[0]

    def embed_batch(self, texts: list[str], prefix: str = "Represent this document for retrieval: ") -> list[list[float]]:
        if not texts:
            return []

        prefixed = [f"{prefix}{t}" if prefix else t for t in texts]

        try:
            model = self._load_primary()
            embeddings = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
            return [e.tolist() for e in embeddings]
        except Exception as exc:
            logger.warning("primary_embedding_failed", error=str(exc))
            fallback = self._load_fallback()
            if fallback is None:
                raise RuntimeError(f"Embedding failed and no fallback available: {exc}") from exc
            embeddings = fallback.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
            self._dimension = len(embeddings[0])
            return [e.tolist() for e in embeddings]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_text(query, prefix="Represent this sentence for searching relevant passages: ")

    def get_model_info(self) -> dict[str, Any]:
        return {
            "primary_model": self.model_name,
            "fallback_model": settings.EMBEDDING_FALLBACK_MODEL,
            "dimension": self._dimension,
        }


embedding_service = EmbeddingService()
