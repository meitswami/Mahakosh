from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cfo.service import CFOService
from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole
from backend.schemas.cfo import CEOBriefingResponse, RecommendationReviewRequest

router = APIRouter()


@router.get("/briefing", response_model=CEOBriefingResponse)
async def ceo_briefing(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = 30,
) -> dict[str, Any]:
    """CEO Mode — instant answers to what happened, what's happening, what needs attention, what's next."""
    svc = CFOService(db)
    briefing = await svc.get_ceo_briefing(current_user.tenant_id, current_user.id, days)
    await db.commit()
    return briefing


@router.get("/capabilities")
async def cfo_capabilities(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = CFOService(db)
    return {"capabilities": await svc.list_capabilities()}


@router.get("/recommendations")
async def list_recommendations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = CFOService(db)
    return {"recommendations": await svc.list_recommendations(current_user.tenant_id)}


@router.post("/recommendations/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: UUID,
    request: RecommendationReviewRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = CFOService(db)
    result = await svc.approve_recommendation(
        current_user.tenant_id, recommendation_id, current_user.id, request.notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Approval failed"))
    await db.commit()
    return result


@router.post("/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: UUID,
    request: RecommendationReviewRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    svc = CFOService(db)
    result = await svc.reject_recommendation(
        current_user.tenant_id, recommendation_id, current_user.id, request.notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Rejection failed"))
    await db.commit()
    return result
