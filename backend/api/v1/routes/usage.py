from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.platform_auth import require_platform_admin
from backend.platform.service import PlatformService

router = APIRouter()


@router.get("")
async def get_usage(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
    tenant_id: UUID | None = None,
) -> dict[str, Any]:
    if tenant_id and not current_user.user.is_platform_admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    target = tenant_id if current_user.user.is_platform_admin and tenant_id else current_user.tenant_id
    svc = PlatformService(db)
    return await svc.get_usage(target, days)
