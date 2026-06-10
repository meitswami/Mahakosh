from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.knowledge.retrieval_engine import RetrievalEngine
from backend.services.knowledge.types import SearchMode


class ChatRetrievalService:
    """RAG retrieval via Knowledge APIs — hybrid search with reranking."""

    def __init__(self, db: AsyncSession):
        self._engine = RetrievalEngine(db)

    async def retrieve(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
        collection_slug: str | None = None,
        user_id: UUID | None = None,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        try:
            search_mode = SearchMode(mode)
        except ValueError:
            search_mode = SearchMode.HYBRID

        response = await self._engine.search(
            tenant_id=tenant_id,
            query=query,
            mode=search_mode,
            top_k=top_k,
            filters=filters,
            collection_slug=collection_slug,
            user_id=user_id,
            rerank=True,
        )
        return {
            "query": response.query,
            "query_id": response.query_id,
            "mode": response.mode,
            "results": response.results,
            "citations": response.citations,
            "total_found": response.total_found,
            "processing_time_ms": response.processing_time_ms,
        }

    async def get_context(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 8,
        filters: dict | None = None,
    ) -> dict[str, Any]:
        return await self._engine.get_context_for_llm(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
            filters=filters,
        )
