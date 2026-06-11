from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.platform_auth import require_platform_admin
from backend.platform.plans import PLAN_DEFINITIONS, get_plan
from backend.platform.service import PlatformService
from backend.schemas.platform import FeatureFlagRequest

router = APIRouter()


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    return {
        "plans": [
            {"tier": tier, **{k: v for k, v in plan.items() if k != "features"}}
            for tier, plan in PLAN_DEFINITIONS.items()
        ]
    }


@router.get("")
async def list_subscriptions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: UUID | None = None,
) -> dict[str, Any]:
    if tenant_id and not current_user.user.is_platform_admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    target = tenant_id or current_user.tenant_id
    svc = PlatformService(db)
    subs = await svc.get_subscriptions(target if not current_user.user.is_platform_admin else tenant_id)
    if not current_user.user.is_platform_admin:
        subs = [s for s in subs if s["tenant_id"] == str(current_user.tenant_id)]
    return {"subscriptions": subs}


@router.get("/current")
async def current_subscription(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = PlatformService(db)
    detail = await svc.get_tenant_detail(current_user.tenant_id)
    plan_tier = detail["tenant"]["subscription_tier"] if detail else "starter"
    return {
        "plan": get_plan(plan_tier),
        "subscription": detail.get("subscription") if detail else None,
        "features": detail.get("features") if detail else {},
        "usage": detail.get("usage") if detail else {},
    }


@router.post("/feature-flags")
async def set_feature_flag(
    request: FeatureFlagRequest,
    current_user: Annotated[CurrentUser, Depends(require_platform_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: UUID = Query(...),
) -> dict[str, Any]:
    svc = PlatformService(db)
    result = await svc.set_feature_flag(tenant_id, request.feature_key, request.enabled, current_user.id, request.reason)
    await db.commit()
    return result
