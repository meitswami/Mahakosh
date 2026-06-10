from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeIndexStatus,
)
from backend.services.knowledge.embedding_service import embedding_service
from backend.services.knowledge.knowledge_chunker import KnowledgeChunker
from backend.services.knowledge.metadata_service import MetadataService
from backend.services.knowledge.qdrant_service import qdrant_service
from backend.services.knowledge.types import ChunkResult, KnowledgeObject

logger = structlog.get_logger(__name__)


class KnowledgeIndexer:
    """Indexes knowledge objects: chunk → embed → PostgreSQL + Qdrant."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunker = KnowledgeChunker()
        self.metadata_service = MetadataService()

    async def index_object(
        self,
        tenant_id: UUID,
        obj: KnowledgeObject,
        user_id: UUID | None = None,
        source_id: UUID | None = None,
        collection_id: UUID | None = None,
    ) -> KnowledgeDocument:
        meta = self.metadata_service.extract_from_object(obj)
        collection_slug = meta["collection_slug"]

        doc = KnowledgeDocument(
            tenant_id=tenant_id,
            collection_id=collection_id,
            source_id=source_id,
            title=obj.title,
            document_type=obj.document_type,
            source=obj.source,
            raw_text=obj.raw_text,
            structured_fields=obj.structured_fields,
            tables=obj.tables,
            metadata_=obj.metadata,
            index_status=KnowledgeIndexStatus.INDEXING,
            confidence=obj.confidence,
            vendor_name=meta.get("vendor_name"),
            customer_name=meta.get("customer_name"),
            gstin=meta.get("gstin"),
            invoice_number=meta.get("invoice_number"),
            document_date=meta.get("document_date"),
            amount=meta.get("amount"),
            tags=obj.tags,
            created_by=user_id,
        )
        self.db.add(doc)
        await self.db.flush()

        chunks = self.chunker.chunk_all(
            text=obj.raw_text or "",
            tables=obj.tables,
            metadata=meta,
        )

        tenant_str = str(tenant_id)
        qdrant_collection = qdrant_service.ensure_collection(
            tenant_str,
            collection_slug,
            embedding_service.dimension,
        )

        chunk_texts = [c.content for c in chunks]
        vectors = embedding_service.embed_batch(chunk_texts) if chunk_texts else []

        qdrant_points = []
        for chunk_result, vector in zip(chunks, vectors):
            chunk_row = await self._persist_chunk(tenant_id, doc.id, chunk_result)
            point_id = str(uuid4())

            payload = self.metadata_service.build_qdrant_payload(
                tenant_id=tenant_str,
                document_id=str(doc.id),
                chunk_id=str(chunk_row.id),
                chunk_index=chunk_result.chunk_index,
                content=chunk_result.content,
                metadata={**meta, "page_number": chunk_result.page_number},
            )

            qdrant_points.append({
                "id": point_id,
                "vector": vector,
                "payload": payload,
            })

            self.db.add(KnowledgeEmbedding(
                tenant_id=tenant_id,
                chunk_id=chunk_row.id,
                document_id=doc.id,
                model_name=embedding_service.model_name,
                qdrant_collection=qdrant_collection,
                qdrant_point_id=point_id,
                vector_dimension=len(vector),
            ))

        if qdrant_points:
            qdrant_service.upsert_vectors(qdrant_collection, qdrant_points)

        await self._update_search_vector(doc, chunks)

        doc.index_status = KnowledgeIndexStatus.INDEXED
        doc.indexed_at = datetime.now(UTC)
        doc.chunk_count = len(chunks)
        await self.db.flush()

        logger.info(
            "knowledge_indexed",
            document_id=str(doc.id),
            chunks=len(chunks),
            collection=collection_slug,
        )
        return doc

    async def _persist_chunk(
        self,
        tenant_id: UUID,
        document_id: UUID,
        chunk: ChunkResult,
    ) -> KnowledgeChunk:
        row = KnowledgeChunk(
            tenant_id=tenant_id,
            document_id=document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            page_number=chunk.page_number,
            metadata_=chunk.metadata,
        )
        self.db.add(row)
        await self.db.flush()

        await self.db.execute(
            text(
                "UPDATE knowledge_chunks SET search_vector = to_tsvector('english', :content) WHERE id = :id"
            ),
            {"content": chunk.content, "id": row.id},
        )
        return row

    async def _update_search_vector(self, doc: KnowledgeDocument, chunks: list[ChunkResult]) -> None:
        full_text = doc.raw_text or " ".join(c.content for c in chunks)
        await self.db.execute(
            text(
                "UPDATE knowledge_documents SET search_vector = to_tsvector('english', :content) WHERE id = :id"
            ),
            {"content": f"{doc.title} {full_text}"[:100000], "id": doc.id},
        )
