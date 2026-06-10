from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledge import KnowledgeCollection, KnowledgeDocument, KnowledgeSource
from backend.services.knowledge.knowledge_graph_builder import KnowledgeGraphBuilder
from backend.services.knowledge.knowledge_indexer import KnowledgeIndexer
from backend.services.knowledge.knowledge_ingestion import KnowledgeIngestion
from backend.services.knowledge.knowledge_validator import KnowledgeValidator
from backend.services.knowledge.qdrant_service import qdrant_service
from backend.services.knowledge.embedding_service import embedding_service
from backend.services.knowledge.types import KnowledgeObject, QdrantCollectionType

logger = structlog.get_logger(__name__)

DEFAULT_COLLECTIONS = [
    ("Invoices", "invoices", "invoices"),
    ("GST", "gst", "knowledge"),
    ("Inventory", "inventory", "knowledge"),
    ("HR", "hr", "knowledge"),
    ("Legal", "legal", "knowledge"),
    ("Accounting", "accounting", "knowledge"),
    ("General Documents", "general", "documents"),
]


class KnowledgeOrchestrator:
    """End-to-end knowledge ingestion, validation, indexing, and graph building."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ingestion = KnowledgeIngestion()
        self.validator = KnowledgeValidator()
        self.indexer = KnowledgeIndexer(db)
        self.graph_builder = KnowledgeGraphBuilder(db)

    async def ensure_default_collections(self, tenant_id: UUID) -> list[KnowledgeCollection]:
        collections = []
        for name, slug, ctype in DEFAULT_COLLECTIONS:
            result = await self.db.execute(
                select(KnowledgeCollection).where(
                    KnowledgeCollection.tenant_id == tenant_id,
                    KnowledgeCollection.slug == slug,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                collections.append(existing)
                continue

            col = KnowledgeCollection(
                tenant_id=tenant_id,
                name=name,
                slug=slug,
                collection_type=ctype,
                is_system=True,
            )
            self.db.add(col)
            collections.append(col)

        await self.db.flush()
        qdrant_service.ensure_tenant_collections(str(tenant_id), embedding_service.dimension)
        return collections

    async def index_object(
        self,
        tenant_id: UUID,
        obj: KnowledgeObject,
        user_id: UUID | None = None,
    ) -> KnowledgeDocument:
        validation = self.validator.validate(obj)
        if not validation["is_valid"]:
            logger.warning("knowledge_validation_issues", issues=validation["issues"])

        source = await self._create_source(tenant_id, obj)
        collection = await self._resolve_collection(tenant_id, obj)

        document = await self.indexer.index_object(
            tenant_id=tenant_id,
            obj=obj,
            user_id=user_id,
            source_id=source.id,
            collection_id=collection.id if collection else None,
        )

        relationships = await self.graph_builder.build_from_object(tenant_id, document, obj)
        document.metadata_ = {
            **document.metadata_,
            "validation": validation,
            "relationship_count": len(relationships),
            "graph_export": self.graph_builder.to_neo4j_export(relationships),
        }

        if collection:
            collection.document_count += 1
            collection.chunk_count += document.chunk_count

        await self.db.flush()
        logger.info("knowledge_orchestrated", document_id=str(document.id), title=obj.title)
        return document

    async def index_from_ocr(self, tenant_id: UUID, ocr_knowledge: dict, user_id: UUID | None = None) -> KnowledgeDocument:
        obj = self.ingestion.from_ocr_result(ocr_knowledge)
        return await self.index_object(tenant_id, obj, user_id)

    async def index_from_file(
        self,
        tenant_id: UUID,
        file_name: str,
        data: bytes,
        user_id: UUID | None = None,
        document_type: str = "general",
    ) -> KnowledgeDocument:
        obj = self.ingestion.from_file_bytes(file_name, data)
        obj.document_type = document_type
        return await self.index_object(tenant_id, obj, user_id)

    async def index_from_text(
        self,
        tenant_id: UUID,
        title: str,
        text: str,
        document_type: str = "general",
        structured_fields: dict | None = None,
        user_id: UUID | None = None,
    ) -> KnowledgeDocument:
        obj = self.ingestion.from_text(title, text, document_type, structured_fields=structured_fields or {})
        return await self.index_object(tenant_id, obj, user_id)

    async def _create_source(self, tenant_id: UUID, obj: KnowledgeObject) -> KnowledgeSource:
        source = KnowledgeSource(
            tenant_id=tenant_id,
            source_type=obj.metadata.get("ingestion", "knowledge_pipeline"),
            source_name=obj.source,
            source_uri=obj.metadata.get("source_uri"),
            original_document_id=obj.document_id,
            ocr_job_id=UUID(obj.metadata["job_id"]) if obj.metadata.get("job_id") else None,
            workflow_id=UUID(obj.metadata["workflow_id"]) if obj.metadata.get("workflow_id") else None,
            metadata_=obj.metadata,
        )
        self.db.add(source)
        await self.db.flush()
        return source

    async def _resolve_collection(
        self,
        tenant_id: UUID,
        obj: KnowledgeObject,
    ) -> KnowledgeCollection | None:
        from backend.services.knowledge.metadata_service import MetadataService
        slug = MetadataService().resolve_collection_slug(obj.document_type, obj.collection_slug)

        result = await self.db.execute(
            select(KnowledgeCollection).where(
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.slug == slug,
            )
        )
        col = result.scalar_one_or_none()
        if col:
            return col

        result = await self.db.execute(
            select(KnowledgeCollection).where(
                KnowledgeCollection.tenant_id == tenant_id,
                KnowledgeCollection.slug == "general",
            )
        )
        return result.scalar_one_or_none()
