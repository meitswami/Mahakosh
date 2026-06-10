import time
from typing import Any

from backend.agents.base import AgentContext, AgentResult, BaseAgent
from backend.core.database import async_session_factory
from backend.services.knowledge.retrieval_engine import RetrievalEngine
from backend.services.knowledge.types import SearchMode


class SearchAgent(BaseAgent):
    name = "search"
    version = "1.0.0"
    description = "Semantic search across documents and knowledge base"
    capabilities = ["semantic_search", "vector_retrieval", "context_ranking", "hybrid_search"]

    async def execute(self, input_data: dict[str, Any], context: AgentContext) -> AgentResult:
        start = time.perf_counter()
        query = input_data.get("query", "").strip()
        if not query:
            return AgentResult(success=False, error="query is required")

        mode_str = input_data.get("mode", "hybrid")
        try:
            mode = SearchMode(mode_str)
        except ValueError:
            mode = SearchMode.HYBRID

        top_k = int(input_data.get("top_k", 20))
        rerank = bool(input_data.get("rerank", True))
        filters = input_data.get("filters")
        collection_slug = input_data.get("collection_slug")

        async with async_session_factory() as db:
            engine = RetrievalEngine(db)
            response = await engine.search(
                tenant_id=context.tenant_id,
                query=query,
                mode=mode,
                top_k=top_k,
                filters=filters,
                collection_slug=collection_slug,
                user_id=context.user_id,
                rerank=rerank,
            )
            await db.commit()

        elapsed = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            success=True,
            data={
                "query": query,
                "mode": response.mode,
                "query_id": str(response.query_id) if response.query_id else None,
                "total_count": response.total_found,
                "processing_time_ms": response.processing_time_ms,
                "results": [
                    {
                        "chunk_id": str(r.chunk_id),
                        "document_id": str(r.document_id),
                        "content": r.content,
                        "score": r.score,
                        "document_title": r.document_title,
                        "document_type": r.document_type,
                        "source_name": r.source_name,
                        "page_number": r.page_number,
                        "metadata": r.metadata,
                    }
                    for r in response.results
                ],
                "citations": response.citations,
            },
            processing_time_ms=elapsed,
            next_agents=["master_orchestrator"],
        )
