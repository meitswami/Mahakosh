from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import ChatMemory, SavedQuery


class MemoryManager:
    """Session memory, long-term memory, and saved queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_session_context(self, session_id: UUID, tenant_id: UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(ChatMemory).where(
                ChatMemory.session_id == session_id,
                ChatMemory.tenant_id == tenant_id,
                ChatMemory.memory_type == "session",
            )
        )
        return [m.value for m in result.scalars().all()]

    async def save_session_memory(
        self,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID,
        key: str,
        value: dict[str, Any],
    ) -> None:
        existing = await self.db.execute(
            select(ChatMemory).where(
                ChatMemory.tenant_id == tenant_id,
                ChatMemory.session_id == session_id,
                ChatMemory.memory_type == "session",
                ChatMemory.key == key,
            )
        )
        mem = existing.scalar_one_or_none()
        if mem:
            mem.value = value
        else:
            self.db.add(ChatMemory(
                tenant_id=tenant_id,
                user_id=user_id,
                memory_type="session",
                key=key,
                value=value,
                session_id=session_id,
            ))

    async def get_long_term(self, tenant_id: UUID, user_id: UUID, key: str) -> dict | None:
        result = await self.db.execute(
            select(ChatMemory).where(
                ChatMemory.tenant_id == tenant_id,
                ChatMemory.user_id == user_id,
                ChatMemory.memory_type == "long_term",
                ChatMemory.key == key,
            )
        )
        mem = result.scalar_one_or_none()
        return mem.value if mem else None

    async def save_long_term(
        self,
        tenant_id: UUID,
        user_id: UUID,
        key: str,
        value: dict[str, Any],
    ) -> None:
        existing = await self.db.execute(
            select(ChatMemory).where(
                ChatMemory.tenant_id == tenant_id,
                ChatMemory.user_id == user_id,
                ChatMemory.memory_type == "long_term",
                ChatMemory.key == key,
            )
        )
        mem = existing.scalar_one_or_none()
        if mem:
            mem.value = value
        else:
            self.db.add(ChatMemory(
                tenant_id=tenant_id,
                user_id=user_id,
                memory_type="long_term",
                key=key,
                value=value,
            ))

    async def record_recent_query(
        self,
        tenant_id: UUID,
        user_id: UUID,
        query: str,
        chat_type: str,
        intent: str,
    ) -> None:
        key = "recent_queries"
        existing = await self.get_long_term(tenant_id, user_id, key) or {"queries": []}
        queries = existing.get("queries", [])
        queries.insert(0, {
            "query": query,
            "chat_type": chat_type,
            "intent": intent,
            "at": datetime.now(UTC).isoformat(),
        })
        existing["queries"] = queries[:20]
        await self.save_long_term(tenant_id, user_id, key, existing)

    async def save_query(
        self,
        tenant_id: UUID,
        user_id: UUID,
        name: str,
        query_text: str,
        chat_type: str = "general",
        intent: str | None = None,
        filters: dict | None = None,
    ) -> SavedQuery:
        sq = SavedQuery(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            query_text=query_text,
            chat_type=chat_type,
            intent=intent,
            filters=filters or {},
        )
        self.db.add(sq)
        await self.db.flush()
        return sq

    async def list_saved_queries(self, tenant_id: UUID, user_id: UUID, limit: int = 20) -> list[SavedQuery]:
        result = await self.db.execute(
            select(SavedQuery)
            .where(SavedQuery.tenant_id == tenant_id, SavedQuery.user_id == user_id)
            .order_by(SavedQuery.usage_count.desc(), SavedQuery.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
