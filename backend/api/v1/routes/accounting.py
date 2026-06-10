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
from backend.models.voucher import VoucherDraft

router = APIRouter()


class VoucherResponse(BaseModel):
    id: UUID
    voucher_type: str
    voucher_number: str | None
    status: str
    total_amount: float

    model_config = {"from_attributes": True}


@router.get("/vouchers", response_model=PaginatedResponse[VoucherResponse])
async def list_vouchers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
) -> PaginatedResponse[VoucherResponse]:
    repo = BaseRepository(db, VoucherDraft)
    items, total = await repo.list_paginated(current_user.tenant_id, page, page_size)
    return PaginatedResponse(
        items=[VoucherResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/ledgers")
async def list_ledgers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {"ledgers": [], "total": 0}


@router.get("/vendors")
async def list_vendors(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {"vendors": [], "total": 0}


@router.get("/customers")
async def list_customers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {"customers": [], "total": 0}


@router.post("/vouchers/{voucher_id}/approve", status_code=202)
async def approve_voucher(
    voucher_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
) -> dict:
    return {"voucher_id": str(voucher_id), "status": "approval_queued"}
