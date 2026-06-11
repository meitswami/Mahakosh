from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.platform_auth import require_platform_admin
from backend.core.security import UserRole
from backend.platform.governance import GovernanceService
from backend.platform.plans import PLAN_DEFINITIONS
from backend.platform.service import PlatformService
from backend.schemas.platform import (
    FeatureFlagRequest,
    LicenseCreateRequest,
    PartnerClientProvisionRequest,
    PartnerRegisterRequest,
    TenantBrandingUpdate,
    TenantCreateRequest,
)

router = APIRouter()


@router.post("/create", status_code=201)
async def create_tenant(
    request: TenantCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = PlatformService(db)
    try:
        result = await svc.create_tenant(
            name=request.name,
            slug=request.slug,
            admin_email=request.admin_email,
            admin_password=request.admin_password,
            admin_full_name=request.admin_full_name,
            tenant_type=request.tenant_type,
            plan_tier=request.plan_tier,
            billing_cycle=request.billing_cycle,
            created_by=current_user.id,
            branding=request.branding,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("")
async def list_tenants(
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_type: str | None = None,
) -> dict[str, Any]:
    svc = PlatformService(db)
    return await svc.list_tenants(page=page, page_size=page_size, tenant_type=tenant_type)


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    if not current_user.user.is_platform_admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    svc = PlatformService(db)
    detail = await svc.get_tenant_detail(tenant_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return detail


@router.put("/{tenant_id}/branding")
async def update_branding(
    tenant_id: UUID,
    request: TenantBrandingUpdate,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    if current_user.tenant_id != tenant_id and not current_user.user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    svc = PlatformService(db)
    result = await svc.update_branding(tenant_id, request.model_dump(exclude_none=True))
    await db.commit()
    return result


@router.get("/{tenant_id}/compliance")
async def compliance_center(
    tenant_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    if current_user.tenant_id != tenant_id and not current_user.user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    gov = GovernanceService(db)
    return await gov.get_compliance_center(tenant_id)
