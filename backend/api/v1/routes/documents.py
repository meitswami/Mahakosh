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
from backend.schemas.common import MessageResponse, PaginatedResponse
from backend.models.document import Document

router = APIRouter()


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    document_type: str
    status: str
    file_name: str
    file_size: int
    mime_type: str

    model_config = {"from_attributes": True}


class DocumentCreateRequest(BaseModel):
    title: str
    document_type: str = "other"


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[DocumentResponse]:
    repo = BaseRepository(db, Document)
    items, total = await repo.list_paginated(current_user.tenant_id, page, page_size)
    return PaginatedResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    repo = BaseRepository(db, Document)
    document = await repo.get_by_id(document_id, current_user.tenant_id)
    if document is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Document not found")
    return DocumentResponse.model_validate(document)


@router.post("", response_model=MessageResponse, status_code=201)
async def create_document(
    request: DocumentCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
) -> MessageResponse:
    return MessageResponse(
        message="Document upload endpoint ready",
        detail=f"Title: {request.title}, Type: {request.document_type}",
    )


@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
) -> MessageResponse:
    return MessageResponse(message="Document deletion endpoint ready", detail=str(document_id))
