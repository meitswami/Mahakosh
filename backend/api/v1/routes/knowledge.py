from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.dependencies import require_role
from backend.core.security import UserRole
from backend.models.knowledge import KnowledgeCollection, KnowledgeDocument, KnowledgeQuery
from backend.models.ocr_job import OCRJob
from backend.schemas.knowledge import (
    KnowledgeChunkResponse,
    KnowledgeCollectionResponse,
    KnowledgeDocumentResponse,
    KnowledgeGraphResponse,
    KnowledgeIndexRequest,
    KnowledgeOverviewResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResultItem,
    KnowledgeCitationResponse,
)
from backend.services.knowledge.knowledge_orchestrator import KnowledgeOrchestrator
from backend.services.knowledge.retrieval_engine import RetrievalEngine
from backend.services.knowledge.types import SearchMode

router = APIRouter()


@router.post("/index", response_model=KnowledgeDocumentResponse, status_code=201)
async def index_knowledge(
    request: KnowledgeIndexRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeDocumentResponse:
    orchestrator = KnowledgeOrchestrator(db)

    if request.ocr_job_id:
        result = await db.execute(
            select(OCRJob).where(
                OCRJob.id == request.ocr_job_id,
                OCRJob.tenant_id == current_user.tenant_id,
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "OCR job not found")
        if not job.knowledge_document:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "OCR job has no knowledge document")
        doc = await orchestrator.index_from_ocr(
            current_user.tenant_id, job.knowledge_document, current_user.id
        )
        return KnowledgeDocumentResponse.model_validate(doc)

    if not request.text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "text or ocr_job_id is required")

    doc = await orchestrator.index_from_text(
        tenant_id=current_user.tenant_id,
        title=request.title or "Knowledge Document",
        text=request.text,
        document_type=request.document_type,
        structured_fields=request.structured_fields,
        user_id=current_user.id,
    )
    return KnowledgeDocumentResponse.model_validate(doc)


@router.post("/index/upload", response_model=KnowledgeDocumentResponse, status_code=201)
async def index_upload(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    document_type: str = Form("general"),
    title: str | None = Form(None),
) -> KnowledgeDocumentResponse:
    data = await file.read()
    orchestrator = KnowledgeOrchestrator(db)
    doc = await orchestrator.index_from_file(
        tenant_id=current_user.tenant_id,
        file_name=file.filename or "upload",
        data=data,
        user_id=current_user.id,
        document_type=document_type,
    )
    if title:
        doc.title = title
    return KnowledgeDocumentResponse.model_validate(doc)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeSearchResponse:
    engine = RetrievalEngine(db)
    try:
        mode = SearchMode(request.mode)
    except ValueError:
        mode = SearchMode.HYBRID

    response = await engine.search(
        tenant_id=current_user.tenant_id,
        query=request.query,
        mode=mode,
        top_k=request.top_k,
        filters=request.filters,
        collection_slug=request.collection_slug,
        user_id=current_user.id,
        rerank=request.rerank,
    )

    items = []
    for i, result in enumerate(response.results):
        citation = response.citations[i] if i < len(response.citations) else None
        items.append(KnowledgeSearchResultItem(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            content=result.content,
            score=result.score,
            document_title=result.document_title,
            document_type=result.document_type,
            source_name=result.source_name,
            page_number=result.page_number,
            metadata=result.metadata,
            citation=KnowledgeCitationResponse(**citation) if citation else None,
        ))

    return KnowledgeSearchResponse(
        query_id=response.query_id,
        query=response.query,
        mode=response.mode,
        results=items,
        citations=[KnowledgeCitationResponse(**c) for c in response.citations],
        processing_time_ms=response.processing_time_ms,
        total_found=response.total_found,
    )


@router.post("/hybrid-search", response_model=KnowledgeSearchResponse)
async def hybrid_search(
    request: KnowledgeSearchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeSearchResponse:
    request.mode = "hybrid"
    return await search_knowledge(request, current_user, db)


@router.post("/semantic-search", response_model=KnowledgeSearchResponse)
async def semantic_search(
    request: KnowledgeSearchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeSearchResponse:
    request.mode = "semantic"
    return await search_knowledge(request, current_user, db)


@router.get("/document/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeDocumentResponse:
    engine = RetrievalEngine(db)
    doc = await engine.get_document(current_user.tenant_id, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge document not found")
    return KnowledgeDocumentResponse.model_validate(doc)


@router.get("/chunk/{chunk_id}", response_model=KnowledgeChunkResponse)
async def get_chunk(
    chunk_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeChunkResponse:
    engine = RetrievalEngine(db)
    chunk = await engine.get_chunk(current_user.tenant_id, chunk_id)
    if not chunk:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge chunk not found")
    return KnowledgeChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        token_count=chunk.token_count,
        chunk_type=chunk.chunk_type,
        page_number=chunk.page_number,
        metadata=chunk.metadata_,
    )


@router.get("/collections", response_model=list[KnowledgeCollectionResponse])
async def list_collections(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[KnowledgeCollectionResponse]:
    orchestrator = KnowledgeOrchestrator(db)
    collections = await orchestrator.ensure_default_collections(current_user.tenant_id)
    return [KnowledgeCollectionResponse.model_validate(c) for c in collections]


@router.get("/overview", response_model=KnowledgeOverviewResponse)
async def knowledge_overview(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeOverviewResponse:
    doc_count = await db.execute(
        select(func.count()).select_from(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == current_user.tenant_id
        )
    )
    from backend.models.knowledge import KnowledgeChunk
    chunk_count = await db.execute(
        select(func.count()).select_from(KnowledgeChunk).where(
            KnowledgeChunk.tenant_id == current_user.tenant_id
        )
    )
    query_count = await db.execute(
        select(func.count()).select_from(KnowledgeQuery).where(
            KnowledgeQuery.tenant_id == current_user.tenant_id
        )
    )

    orchestrator = KnowledgeOrchestrator(db)
    collections = await orchestrator.ensure_default_collections(current_user.tenant_id)

    recent = await db.execute(
        select(KnowledgeQuery)
        .where(KnowledgeQuery.tenant_id == current_user.tenant_id)
        .order_by(KnowledgeQuery.created_at.desc())
        .limit(10)
    )
    recent_queries = [
        {"query": q.query_text, "mode": q.search_mode, "results": q.results_count, "at": q.created_at.isoformat()}
        for q in recent.scalars().all()
    ]

    sources = await db.execute(
        select(KnowledgeDocument.source, func.count())
        .where(KnowledgeDocument.tenant_id == current_user.tenant_id)
        .group_by(KnowledgeDocument.source)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_sources = [{"source": row[0], "count": row[1]} for row in sources.fetchall()]

    return KnowledgeOverviewResponse(
        total_documents=doc_count.scalar() or 0,
        total_chunks=chunk_count.scalar() or 0,
        total_queries=query_count.scalar() or 0,
        collections=[KnowledgeCollectionResponse.model_validate(c) for c in collections],
        top_sources=top_sources,
        recent_queries=recent_queries,
    )


@router.get("/graph/{document_id}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeGraphResponse:
    engine = RetrievalEngine(db)
    doc = await engine.get_document(current_user.tenant_id, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    graph_data = doc.metadata_.get("graph_export", {"nodes": [], "edges": []})
    return KnowledgeGraphResponse(
        document_id=document_id,
        nodes=graph_data.get("nodes", []),
        edges=graph_data.get("edges", []),
    )


@router.post("/context")
async def get_llm_context(
    request: KnowledgeSearchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    engine = RetrievalEngine(db)
    return await engine.get_context_for_llm(
        tenant_id=current_user.tenant_id,
        query=request.query,
        top_k=min(request.top_k, 10),
        filters=request.filters,
    )
