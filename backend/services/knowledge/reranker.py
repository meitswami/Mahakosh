import structlog

from backend.core.config import settings
from backend.services.knowledge.types import RetrievalResult

logger = structlog.get_logger(__name__)


class Reranker:
    """Re-ranks retrieval results using BAAI/bge-reranker-large."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.RERANKER_MODEL
        self._model = None

    def _load_model(self):
        if self._model is None:
            from FlagEmbedding import FlagReranker
            logger.info("loading_reranker_model", model=self.model_name)
            self._model = FlagReranker(self.model_name, use_fp16=False)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        if not results:
            return []

        top_k = top_k or settings.RERANK_TOP_K
        pairs = [[query, r.content] for r in results]

        try:
            model = self._load_model()
            scores = model.compute_score(pairs, normalize=True)
            if isinstance(scores, float):
                scores = [scores]
        except Exception as exc:
            logger.warning("reranker_failed_using_original_scores", error=str(exc))
            return results[:top_k]

        scored = list(zip(results, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        reranked: list[RetrievalResult] = []
        for result, score in scored[:top_k]:
            result.score = float(score)
            reranked.append(result)

        return reranked


reranker = Reranker()
