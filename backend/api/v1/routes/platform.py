from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.platform_auth import require_platform_admin
from backend.platform.partner_service import PartnerService
from backend.platform.service import PlatformService
from backend.schemas.platform import PartnerClientProvisionRequest, PartnerRegisterRequest

router = APIRouter()


@router.get("/dashboard")
async def platform_dashboard(
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = PlatformService(db)
    return await svc.get_platform_dashboard()


@router.get("/usage")
async def platform_usage(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
) -> dict[str, Any]:
    svc = PlatformService(db)
    return await svc.get_usage(current_user.tenant_id, days)


@router.post("/partners/register", status_code=201)
async def register_partner(
    request: PartnerRegisterRequest,
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = PartnerService(db)
    partner = await svc.register_partner(
        current_user.tenant_id,
        request.partner_type,
        request.company_name,
        request.contact_email,
        request.max_clients,
    )
    await db.commit()
    return {"partner_id": str(partner.id), "status": partner.status}


@router.post("/partners/clients", status_code=201)
async def provision_partner_client(
    request: PartnerClientProvisionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from sqlalchemy import select
    from backend.models.platform import PartnerAccount

    result = await db.execute(
        select(PartnerAccount).where(PartnerAccount.tenant_id == current_user.tenant_id)
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=403, detail="Partner account required")

    svc = PartnerService(db)
    try:
        client = await svc.provision_client(
            partner.id,
            name=request.name,
            slug=request.slug,
            admin_email=request.admin_email,
            admin_password=request.admin_password,
            admin_full_name=request.admin_full_name,
            plan_tier=request.plan_tier,
        )
        await db.commit()
        return client
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/partners/dashboard")
async def partner_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from sqlalchemy import select
    from backend.models.platform import PartnerAccount

    result = await db.execute(
        select(PartnerAccount).where(PartnerAccount.tenant_id == current_user.tenant_id)
    )
    partner = result.scalar_one_or_none()
    if not partner:
        return {"partner": None, "clients": []}

    svc = PartnerService(db)
    return await svc.get_partner_dashboard(partner.id)
