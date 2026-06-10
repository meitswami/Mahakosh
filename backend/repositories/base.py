from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: UUID, tenant_id: UUID) -> ModelType | None:
        result = await self.db.execute(
            select(self.model).where(self.model.id == id, self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ModelType], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(self.model).where(self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(self.model)
            .where(self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
            .offset(offset)
            .limit(page_size)
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        )
        items = list(result.scalars().all())
        return items, total

    async def create(self, entity: ModelType) -> ModelType:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        await self.db.delete(entity)
        await self.db.flush()
