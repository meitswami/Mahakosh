from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.dependencies import require_role
from backend.core.security import UserRole
from backend.repositories.base import BaseRepository
from backend.schemas.common import PaginatedResponse
from backend.models.audit import AuditLog

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None
    description: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.AUDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    entity_type: str | None = None,
) -> PaginatedResponse[AuditLogResponse]:
    repo = BaseRepository(db, AuditLog)
    items, total = await repo.list_paginated(current_user.tenant_id, page, page_size)
    return PaginatedResponse(
        items=[
            AuditLogResponse(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                description=log.description,
                created_at=log.created_at.isoformat(),
            )
            for log in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/approvals")
async def list_pending_approvals(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
) -> dict:
    return {"approvals": [], "total": 0}
