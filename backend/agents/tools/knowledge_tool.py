"""Knowledge access layer — the ONLY way agents may read document/OCR/business data."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.knowledge.retrieval_engine import RetrievalEngine
from backend.services.knowledge.types import SearchMode


class KnowledgeTool:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._engine = RetrievalEngine(db)

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        mode: str = "hybrid",
        top_k: int = 20,
        filters: dict | None = None,
        collection_slug: str | None = None,
        user_id: UUID | None = None,
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
            "mode": response.mode,
            "query_id": str(response.query_id) if response.query_id else None,
            "total_found": response.total_found,
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
        }

    async def get_context(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> dict[str, Any]:
        return await self._engine.get_context_for_llm(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
            filters=filters,
        )

    async def get_document(self, tenant_id: UUID, document_id: UUID) -> dict[str, Any] | None:
        doc = await self._engine.get_document(tenant_id, document_id)
        if not doc:
            return None
        return {
            "id": str(doc.id),
            "title": doc.title,
            "document_type": doc.document_type,
            "source": doc.source,
            "raw_text": doc.raw_text,
            "structured_fields": doc.structured_fields,
            "tables": doc.tables,
            "metadata": doc.metadata_,
            "vendor_name": doc.vendor_name,
            "customer_name": doc.customer_name,
            "gstin": doc.gstin,
            "invoice_number": doc.invoice_number,
            "document_date": doc.document_date,
            "amount": doc.amount,
            "confidence": doc.confidence,
            "chunk_count": doc.chunk_count,
        }

    async def get_chunk(self, tenant_id: UUID, chunk_id: UUID) -> dict[str, Any] | None:
        chunk = await self._engine.get_chunk(tenant_id, chunk_id)
        if not chunk:
            return None
        return {
            "id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "metadata": chunk.metadata_,
        }
