from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.tools.knowledge_tool import KnowledgeTool


class KnowledgeMemory:
    """Agent-facing knowledge memory backed by Retrieval Engine."""

    def __init__(self, db: AsyncSession):
        self._tool = KnowledgeTool(db)

    async def recall(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> dict[str, Any]:
        return await self._tool.search(tenant_id, query, top_k=top_k, filters=filters)

    async def get_context(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return await self._tool.get_context(tenant_id, query, top_k=top_k)

    async def get_document(self, tenant_id: UUID, document_id: UUID) -> dict[str, Any] | None:
        return await self._tool.get_document(tenant_id, document_id)
