from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import ChatContextRecord, ChatMessage, ChatSession


class ConversationManager:
    """Manage chat sessions and messages with tenant isolation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID | None = None,
        chat_type: str = "general",
    ) -> ChatSession:
        if session_id:
            result = await self.db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.user_id == user_id,
                )
            )
            session = result.scalar_one_or_none()
            if session:
                return session

        session = ChatSession(
            tenant_id=tenant_id,
            user_id=user_id,
            chat_type=chat_type,
            title="New Conversation",
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def add_message(
        self,
        session: ChatSession,
        role: str,
        content: str,
        *,
        chat_type: str | None = None,
        intent: str | None = None,
        confidence: float | None = None,
        citations: list | None = None,
        structured_data: dict | None = None,
        agents_used: list | None = None,
        reasoning_steps: list | None = None,
        model_used: str | None = None,
        processing_time_ms: int | None = None,
        knowledge_query_id: UUID | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            tenant_id=session.tenant_id,
            session_id=session.id,
            role=role,
            content=content,
            chat_type=chat_type,
            intent=intent,
            confidence=confidence,
            citations=citations or [],
            structured_data=structured_data or {},
            agents_used=agents_used or [],
            reasoning_steps=reasoning_steps or [],
            model_used=model_used,
            processing_time_ms=processing_time_ms,
            knowledge_query_id=knowledge_query_id,
        )
        self.db.add(msg)
        session.message_count += 1
        session.last_message_at = datetime.now(UTC)
        if role == "user" and session.title == "New Conversation":
            session.title = content[:80] + ("..." if len(content) > 80 else "")
        await self.db.flush()
        return msg

    async def save_context(
        self,
        session_id: UUID,
        tenant_id: UUID,
        context_type: str,
        context_data: dict,
        message_id: UUID | None = None,
    ) -> None:
        record = ChatContextRecord(
            tenant_id=tenant_id,
            session_id=session_id,
            message_id=message_id,
            context_type=context_type,
            context_data=context_data,
            token_count=len(str(context_data).split()),
        )
        self.db.add(record)

    async def get_session(self, session_id: UUID, tenant_id: UUID, user_id: UUID) -> ChatSession | None:
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.tenant_id == tenant_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_messages(self, session_id: UUID, tenant_id: UUID, limit: int = 100) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.tenant_id == tenant_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_sessions(self, tenant_id: UUID, user_id: UUID, limit: int = 50) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.tenant_id == tenant_id, ChatSession.user_id == user_id, ChatSession.status == "active")
            .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_session(self, session_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        session = await self.get_session(session_id, tenant_id, user_id)
        if not session:
            return False
        session.status = "deleted"
        return True
