from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser
from backend.core.platform_auth import require_platform_admin
from backend.platform.service import PlatformService
from backend.schemas.platform import LicenseCreateRequest

router = APIRouter()


@router.post("", status_code=201)
async def create_license(
    request: LicenseCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = PlatformService(db)
    result = await svc.create_license(UUID(request.tenant_id), request.plan_tier, request.duration_days)
    await db.commit()
    return result
