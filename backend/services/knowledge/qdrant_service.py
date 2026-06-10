import uuid
from typing import Any

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from backend.core.config import settings
from backend.services.knowledge.types import QdrantCollectionType

logger = structlog.get_logger(__name__)

SYSTEM_COLLECTIONS = [
    QdrantCollectionType.DOCUMENTS,
    QdrantCollectionType.INVOICES,
    QdrantCollectionType.VENDORS,
    QdrantCollectionType.CUSTOMERS,
    QdrantCollectionType.KNOWLEDGE,
    QdrantCollectionType.CHAT_MEMORY,
    QdrantCollectionType.WORKFLOW_MEMORY,
]


class QdrantService:
    """Manages Qdrant vector collections with tenant isolation."""

    def __init__(self):
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
        return self._client

    def collection_name(self, tenant_id: str, collection_type: str) -> str:
        return f"{settings.QDRANT_COLLECTION_PREFIX}_{tenant_id}_{collection_type}"

    def ensure_collection(
        self,
        tenant_id: str,
        collection_type: str,
        vector_size: int,
    ) -> str:
        name = self.collection_name(tenant_id, collection_type)
        collections = [c.name for c in self.client.get_collections().collections]

        if name not in collections:
            self.client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            self.client.create_payload_index(name, "tenant_id", qmodels.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(name, "document_id", qmodels.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(name, "chunk_id", qmodels.PayloadSchemaType.KEYWORD)
            self.client.create_payload_index(name, "document_type", qmodels.PayloadSchemaType.KEYWORD)
            logger.info("qdrant_collection_created", collection=name)

        return name

    def ensure_tenant_collections(self, tenant_id: str, vector_size: int) -> list[str]:
        return [
            self.ensure_collection(tenant_id, ct.value, vector_size)
            for ct in SYSTEM_COLLECTIONS
        ]

    def upsert_vectors(
        self,
        collection_name: str,
        points: list[dict[str, Any]],
    ) -> int:
        qdrant_points = []
        for point in points:
            point_id = point.get("id") or str(uuid.uuid4())
            qdrant_points.append(qmodels.PointStruct(
                id=point_id,
                vector=point["vector"],
                payload=point.get("payload", {}),
            ))

        self.client.upsert(collection_name=collection_name, points=qdrant_points)
        return len(qdrant_points)

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        qdrant_filter = self._build_filter(filters) if filters else None

        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    def search_multi_collection(
        self,
        tenant_id: str,
        collection_types: list[str],
        query_vector: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        all_results: list[dict[str, Any]] = []
        for ct in collection_types:
            name = self.collection_name(tenant_id, ct)
            try:
                results = self.search(name, query_vector, top_k, filters)
                for r in results:
                    r["collection"] = ct
                all_results.extend(results)
            except Exception as exc:
                logger.warning("qdrant_search_failed", collection=name, error=str(exc))

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    def delete_document_vectors(
        self,
        collection_name: str,
        document_id: str,
    ) -> None:
        self.client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    def _build_filter(self, filters: dict[str, Any]) -> qmodels.Filter:
        conditions = []
        for key, value in filters.items():
            if value is not None:
                conditions.append(qmodels.FieldCondition(
                    key=key,
                    match=qmodels.MatchValue(value=str(value)),
                ))
        return qmodels.Filter(must=conditions) if conditions else None


qdrant_service = QdrantService()
