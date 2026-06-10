import time
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery
from backend.services.knowledge.citation_engine import CitationEngine
from backend.services.knowledge.embedding_service import embedding_service
from backend.services.knowledge.metadata_service import MetadataService
from backend.services.knowledge.qdrant_service import qdrant_service
from backend.services.knowledge.reranker import reranker
from backend.services.knowledge.types import QdrantCollectionType, RetrievalResult, SearchMode, SearchResponse

logger = structlog.get_logger(__name__)


class RetrievalEngine:
    """Hybrid retrieval: keyword + vector + metadata with reranking and citations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.citation_engine = CitationEngine()
        self.metadata_service = MetadataService()

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        top_k: int | None = None,
        filters: dict | None = None,
        collection_slug: str | None = None,
        user_id: UUID | None = None,
        rerank: bool = True,
    ) -> SearchResponse:
        start = time.perf_counter()
        top_k = top_k or settings.RETRIEVAL_TOP_K
        tenant_str = str(tenant_id)

        if mode == SearchMode.KEYWORD:
            results = await self._keyword_search(tenant_id, query, top_k, filters)
        elif mode == SearchMode.VECTOR or mode == SearchMode.SEMANTIC:
            results = await self._vector_search(tenant_str, query, top_k, filters, collection_slug)
        elif mode == SearchMode.METADATA:
            results = await self._metadata_search(tenant_id, filters or {}, top_k)
        else:
            results = await self._hybrid_search(tenant_id, tenant_str, query, top_k, filters, collection_slug)

        if rerank and results:
            results = reranker.rerank(query, results, settings.RERANK_TOP_K)

        citations = self.citation_engine.build_citations(results)
        elapsed = int((time.perf_counter() - start) * 1000)

        query_record = await self._log_query(
            tenant_id, user_id, query, mode.value, filters, len(results), elapsed, collection_slug
        )

        return SearchResponse(
            query_id=query_record.id if query_record else None,
            query=query,
            mode=mode.value,
            results=results,
            citations=citations,
            processing_time_ms=elapsed,
            total_found=len(results),
        )

    async def get_context_for_llm(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> dict:
        response = await self.search(
            tenant_id=tenant_id,
            query=query,
            mode=SearchMode.HYBRID,
            top_k=top_k,
            filters=filters,
            rerank=True,
        )
        context_parts = []
        for i, result in enumerate(response.results):
            citation = response.citations[i] if i < len(response.citations) else {}
            context_parts.append(
                f"--- Context {i + 1} [{citation.get('citation_text', '')}] ---\n{result.content}"
            )
        return {
            "query": query,
            "context": "\n\n".join(context_parts),
            "citations": response.citations,
            "chunk_ids": [str(r.chunk_id) for r in response.results],
            "document_ids": list({str(r.document_id) for r in response.results}),
        }

    async def get_document(self, tenant_id: UUID, document_id: UUID) -> KnowledgeDocument | None:
        result = await self.db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_chunk(self, tenant_id: UUID, chunk_id: UUID) -> KnowledgeChunk | None:
        result = await self.db.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.id == chunk_id,
                KnowledgeChunk.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def cross_document_search(
        self,
        tenant_id: UUID,
        query: str,
        document_types: list[str] | None = None,
        top_k: int = 10,
    ) -> SearchResponse:
        filters = {"tenant_id": str(tenant_id)}
        if document_types:
            filters["document_type"] = document_types[0]
        return await self.search(tenant_id, query, SearchMode.HYBRID, top_k, filters)

    async def relationship_search(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        from backend.models.knowledge import KnowledgeRelationship

        result = await self.db.execute(
            select(KnowledgeRelationship).where(
                KnowledgeRelationship.tenant_id == tenant_id,
                KnowledgeRelationship.target_entity_type == entity_type,
                KnowledgeRelationship.target_entity_id == entity_id,
            ).limit(top_k)
        )
        rels = list(result.scalars().all())
        results: list[RetrievalResult] = []
        for rel in rels:
            doc = await self.get_document(tenant_id, rel.source_document_id)
            if doc and doc.raw_text:
                results.append(RetrievalResult(
                    chunk_id=uuid4(),
                    document_id=doc.id,
                    content=doc.raw_text[:1000],
                    score=rel.confidence,
                    document_title=doc.title,
                    document_type=doc.document_type,
                    source_name=doc.source,
                    page_number=None,
                    metadata={"relationship": rel.relationship_type},
                ))
        return results

    async def _hybrid_search(
        self,
        tenant_id: UUID,
        tenant_str: str,
        query: str,
        top_k: int,
        filters: dict | None,
        collection_slug: str | None,
    ) -> list[RetrievalResult]:
        keyword_results = await self._keyword_search(tenant_id, query, top_k, filters)
        vector_results = await self._vector_search(tenant_str, query, top_k, filters, collection_slug)
        return self._reciprocal_rank_fusion(keyword_results, vector_results, top_k)

    async def _keyword_search(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int,
        filters: dict | None,
    ) -> list[RetrievalResult]:
        sql = """
            SELECT c.id as chunk_id, c.document_id, c.content, c.page_number,
                   d.title, d.document_type, d.source,
                   ts_rank(c.search_vector, plainto_tsquery('english', :query)) as rank
            FROM knowledge_chunks c
            JOIN knowledge_documents d ON d.id = c.document_id
            WHERE c.tenant_id = :tenant_id
              AND c.search_vector @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """
        result = await self.db.execute(
            text(sql),
            {"tenant_id": str(tenant_id), "query": query, "limit": top_k},
        )
        rows = result.fetchall()
        return [
            RetrievalResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content,
                score=float(row.rank),
                document_title=row.title,
                document_type=row.document_type,
                source_name=row.source,
                page_number=row.page_number,
                metadata={"search_type": "keyword"},
            )
            for row in rows
        ]

    async def _vector_search(
        self,
        tenant_str: str,
        query: str,
        top_k: int,
        filters: dict | None,
        collection_slug: str | None,
    ) -> list[RetrievalResult]:
        query_vector = embedding_service.embed_query(query)
        qdrant_filters = self.metadata_service.build_search_filters(filters)
        qdrant_filters["tenant_id"] = tenant_str

        collection_types = [collection_slug] if collection_slug else [
            QdrantCollectionType.DOCUMENTS.value,
            QdrantCollectionType.INVOICES.value,
            QdrantCollectionType.KNOWLEDGE.value,
        ]

        hits = qdrant_service.search_multi_collection(
            tenant_str, collection_types, query_vector, top_k, qdrant_filters
        )

        results: list[RetrievalResult] = []
        for hit in hits:
            payload = hit.get("payload", {})
            chunk_id = payload.get("chunk_id")
            doc_id = payload.get("document_id")
            if not chunk_id or not doc_id:
                continue
            results.append(RetrievalResult(
                chunk_id=UUID(chunk_id),
                document_id=UUID(doc_id),
                content=payload.get("content", ""),
                score=hit["score"],
                document_title=payload.get("title", ""),
                document_type=payload.get("document_type", ""),
                source_name=payload.get("source", ""),
                page_number=payload.get("page_number"),
                metadata={"search_type": "vector", "collection": hit.get("collection")},
            ))
        return results

    async def _metadata_search(
        self,
        tenant_id: UUID,
        filters: dict,
        top_k: int,
    ) -> list[RetrievalResult]:
        query = select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id)

        if filters.get("document_type"):
            query = query.where(KnowledgeDocument.document_type == filters["document_type"])
        if filters.get("vendor_name"):
            query = query.where(KnowledgeDocument.vendor_name.ilike(f"%{filters['vendor_name']}%"))
        if filters.get("gstin"):
            query = query.where(KnowledgeDocument.gstin == filters["gstin"])
        if filters.get("invoice_number"):
            query = query.where(KnowledgeDocument.invoice_number == filters["invoice_number"])

        query = query.limit(top_k)
        result = await self.db.execute(query)
        docs = list(result.scalars().all())

        results: list[RetrievalResult] = []
        for doc in docs:
            chunk_result = await self.db.execute(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.document_id == doc.id)
                .order_by(KnowledgeChunk.chunk_index)
                .limit(1)
            )
            chunk = chunk_result.scalar_one_or_none()
            results.append(RetrievalResult(
                chunk_id=chunk.id if chunk else uuid4(),
                document_id=doc.id,
                content=chunk.content if chunk else (doc.raw_text or "")[:1000],
                score=1.0,
                document_title=doc.title,
                document_type=doc.document_type,
                source_name=doc.source,
                page_number=chunk.page_number if chunk else None,
                metadata={"search_type": "metadata"},
            ))
        return results

    def _reciprocal_rank_fusion(
        self,
        list_a: list[RetrievalResult],
        list_b: list[RetrievalResult],
        top_k: int,
        k: int = 60,
    ) -> list[RetrievalResult]:
        scores: dict[str, float] = {}
        items: dict[str, RetrievalResult] = {}

        for rank, item in enumerate(list_a):
            key = str(item.chunk_id)
            scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
            items[key] = item

        for rank, item in enumerate(list_b):
            key = str(item.chunk_id)
            scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
            if key not in items or item.score > items[key].score:
                items[key] = item

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for key, score in ranked:
            item = items[key]
            item.score = score
            item.metadata["search_type"] = "hybrid"
            results.append(item)
        return results

    async def _log_query(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        query: str,
        mode: str,
        filters: dict | None,
        results_count: int,
        elapsed_ms: int,
        collection_slug: str | None,
    ) -> KnowledgeQuery:
        record = KnowledgeQuery(
            tenant_id=tenant_id,
            user_id=user_id,
            query_text=query,
            query_type="search",
            search_mode=mode,
            filters=filters or {},
            results_count=results_count,
            processing_time_ms=elapsed_ms,
            collection_slug=collection_slug,
        )
        self.db.add(record)
        await self.db.flush()
        return record
