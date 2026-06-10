from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.dependencies import require_role
from backend.core.security import UserRole
from backend.models.ocr_job import (
    OCRConfidenceScore,
    OCRJob,
    OCRJobField,
    OCRJobPage,
    OCRJobTable,
    OCRPipelineStage,
    OCRValidationResult,
)
from backend.schemas.ocr import (
    OCRConfidenceResponse,
    OCRFieldResponse,
    OCRJobStatusResponse,
    OCRPageResponse,
    OCRPipelineStageResponse,
    OCRProcessRequest,
    OCRResultResponse,
    OCRTableResponse,
    OCRUploadResponse,
    OCRValidationResponse,
)
from backend.services.ocr_service import OCRService

router = APIRouter()


async def _run_ocr_background(job_id: UUID, tenant_id: UUID) -> None:
    from backend.core.database import async_session_factory

    async with async_session_factory() as session:
        try:
            service = OCRService(session)
            await service.process_job(job_id, tenant_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@router.post("/upload", response_model=OCRUploadResponse, status_code=201)
async def upload_document(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
) -> OCRUploadResponse:
    service = OCRService(db)
    job = await service.upload_and_create_job(
        file=file,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        title=title,
    )
    return OCRUploadResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        file_name=file.filename or "document",
        message="Document uploaded successfully. Call /process to start OCR pipeline.",
    )


@router.post("/process", response_model=OCRJobStatusResponse)
async def process_ocr(
    request: OCRProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    sync: bool = Query(False, description="Run pipeline synchronously (blocks until complete)"),
) -> OCRJobStatusResponse:
    service = OCRService(db)
    job = await service.get_job(request.job_id, current_user.tenant_id)

    if job.language != request.language:
        job.language = request.language
        await db.flush()

    if sync:
        job = await service.process_job(request.job_id, current_user.tenant_id)
    else:
        from backend.models.ocr_job import OCRJobStatus
        job.status = OCRJobStatus.PROCESSING
        await db.flush()
        background_tasks.add_task(_run_ocr_background, request.job_id, current_user.tenant_id)

    return OCRJobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        document_class=job.document_class,
        classification_confidence=job.classification_confidence,
        page_count=job.page_count,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        processing_time_ms=job.processing_time_ms,
        created_at=job.created_at,
    )


@router.get("/status/{job_id}", response_model=OCRJobStatusResponse)
async def get_ocr_status(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OCRJobStatusResponse:
    service = OCRService(db)
    job = await service.get_job(job_id, current_user.tenant_id)
    return OCRJobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        document_class=job.document_class,
        classification_confidence=job.classification_confidence,
        page_count=job.page_count,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        processing_time_ms=job.processing_time_ms,
        created_at=job.created_at,
    )


@router.get("/result/{job_id}", response_model=OCRResultResponse)
async def get_ocr_result(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OCRResultResponse:
    service = OCRService(db)
    job = await service.get_job(job_id, current_user.tenant_id)

    fields_result = await db.execute(
        select(OCRJobField).where(OCRJobField.job_id == job_id, OCRJobField.tenant_id == current_user.tenant_id)
    )
    tables_result = await db.execute(
        select(OCRJobTable).where(OCRJobTable.job_id == job_id, OCRJobTable.tenant_id == current_user.tenant_id)
    )
    pages_result = await db.execute(
        select(OCRJobPage).where(OCRJobPage.job_id == job_id, OCRJobPage.tenant_id == current_user.tenant_id)
    )
    stages_result = await db.execute(
        select(OCRPipelineStage).where(OCRPipelineStage.job_id == job_id).order_by(OCRPipelineStage.started_at)
    )
    confidence_result = await db.execute(
        select(OCRConfidenceScore).where(OCRConfidenceScore.job_id == job_id)
    )

    return OCRResultResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        document_class=job.document_class,
        classification_confidence=job.classification_confidence,
        paddle_output=job.paddle_output,
        surya_output=job.surya_output,
        consensus_output=job.consensus_output,
        fields=[OCRFieldResponse.model_validate(f) for f in fields_result.scalars().all()],
        tables=[OCRTableResponse.model_validate(t) for t in tables_result.scalars().all()],
        pages=[OCRPageResponse.model_validate(p) for p in pages_result.scalars().all()],
        confidence_scores=[OCRConfidenceResponse.model_validate(c) for c in confidence_result.scalars().all()],
        pipeline_stages=[OCRPipelineStageResponse.model_validate(s) for s in stages_result.scalars().all()],
        knowledge_document=job.knowledge_document,
    )


@router.get("/validation/{job_id}", response_model=OCRValidationResponse)
async def get_ocr_validation(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OCRValidationResponse:
    await OCRService(db).get_job(job_id, current_user.tenant_id)

    result = await db.execute(
        select(OCRValidationResult).where(
            OCRValidationResult.job_id == job_id,
            OCRValidationResult.tenant_id == current_user.tenant_id,
        )
    )
    validation = result.scalar_one_or_none()
    if validation is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Validation results not found. Job may still be processing.")

    return OCRValidationResponse(
        job_id=job_id,
        is_valid=validation.is_valid,
        issues=validation.issues,
        checks_passed=validation.checks_passed,
        checks_failed=validation.checks_failed,
    )


@router.get("/jobs")
async def list_ocr_jobs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> dict:
    service = OCRService(db)
    jobs, total = await service.list_jobs(current_user.tenant_id, page, page_size)
    return {
        "items": [
            OCRJobStatusResponse(
                job_id=j.id,
                document_id=j.document_id,
                status=j.status,
                document_class=j.document_class,
                classification_confidence=j.classification_confidence,
                page_count=j.page_count,
                error_message=j.error_message,
                started_at=j.started_at,
                completed_at=j.completed_at,
                processing_time_ms=j.processing_time_ms,
                created_at=j.created_at,
            )
            for j in jobs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }
