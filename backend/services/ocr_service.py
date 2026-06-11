import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import structlog
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.document import Document, DocumentStatus
from backend.models.ocr_job import (
    OCRConfidenceScore,
    OCRJob,
    OCRJobField,
    OCRJobPage,
    OCRJobTable,
    OCRJobStatus,
    OCRPipelineStage,
    OCRValidationResult,
)
from backend.services.document_intelligence.confidence_engine import ConfidenceEngine
from backend.services.document_intelligence.pipeline_orchestrator import PipelineOrchestrator
from backend.services.document_intelligence.types import PipelineResult, StageLog
from backend.services.storage_service import storage_service

logger = structlog.get_logger(__name__)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/webp",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp"}


class OCRService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_and_create_job(
        self,
        file: UploadFile,
        tenant_id: UUID,
        user_id: UUID,
        title: str | None = None,
    ) -> OCRJob:
        if not file.filename:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Filename is required")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {ext}")

        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

        mime = file.content_type or "application/octet-stream"
        storage_path, checksum = storage_service.upload_file(
            tenant_id, file.filename, content, mime
        )

        doc_title = title or file.filename
        document = Document(
            tenant_id=tenant_id,
            title=doc_title,
            document_type="other",
            status=DocumentStatus.UPLOADED,
            file_name=file.filename,
            file_path=storage_path,
            file_size=len(content),
            mime_type=mime,
            checksum=checksum,
            uploaded_by=user_id,
        )
        self.db.add(document)
        await self.db.flush()

        job = OCRJob(
            tenant_id=tenant_id,
            document_id=document.id,
            status=OCRJobStatus.UPLOADED,
            created_by=user_id,
            metadata_={"file_name": file.filename, "mime_type": mime},
        )
        self.db.add(job)
        await self.db.flush()

        from backend.platform.usage_tracker import UsageTracker
        tracker = UsageTracker(self.db)
        await tracker.record(tenant_id, "documents_processed")
        await tracker.record(tenant_id, "ocr_usage")

        return job

    async def process_job(self, job_id: UUID, tenant_id: UUID) -> OCRJob:
        job = await self._get_job(job_id, tenant_id)
        if job.status in (OCRJobStatus.PROCESSING, OCRJobStatus.COMPLETED):
            return job

        result = await self.db.execute(
            select(Document).where(Document.id == job.document_id, Document.tenant_id == tenant_id)
        )
        document = result.scalar_one()

        job.status = OCRJobStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        document.status = DocumentStatus.PROCESSING
        await self.db.flush()

        work_dir = str(Path("storage/temp") / tenant_id.hex / str(job_id))
        os.makedirs(work_dir, exist_ok=True)

        local_file = storage_service.get_local_copy(document.file_path, work_dir)
        stage_records: list[StageLog] = []
        orchestrator = PipelineOrchestrator(work_dir)

        try:
            pipeline_result = orchestrator.run(
                file_path=local_file,
                document_id=document.id,
                job_id=job_id,
                language=job.language,
                title=document.title,
                metadata={"file_name": document.file_name, "mime_type": document.mime_type},
                on_stage_complete=lambda log: stage_records.append(log),
            )
            await self._persist_pipeline_result(job, document, pipeline_result, stage_records)
        except Exception as exc:
            logger.error("ocr_job_failed", job_id=str(job_id), error=str(exc))
            job.status = OCRJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            document.status = DocumentStatus.FAILED
            await self._persist_stage_logs(job, stage_records)
            await self.db.flush()
            raise

        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> OCRJob:
        return await self._get_job(job_id, tenant_id)

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OCRJob], int]:
        from sqlalchemy import func

        count_q = await self.db.execute(
            select(func.count()).select_from(OCRJob).where(OCRJob.tenant_id == tenant_id)
        )
        total = count_q.scalar() or 0

        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(OCRJob)
            .where(OCRJob.tenant_id == tenant_id)
            .order_by(OCRJob.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def _get_job(self, job_id: UUID, tenant_id: UUID) -> OCRJob:
        result = await self.db.execute(
            select(OCRJob).where(OCRJob.id == job_id, OCRJob.tenant_id == tenant_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "OCR job not found")
        return job

    async def _persist_pipeline_result(
        self,
        job: OCRJob,
        document: Document,
        result: PipelineResult,
        stage_logs: list[StageLog],
    ) -> None:
        job.status = OCRJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.page_count = len(result.preprocessed_pages)
        job.document_class = result.classification.document_class.value if result.classification else None
        job.classification_confidence = result.classification.confidence if result.classification else None

        if result.consensus:
            job.paddle_output = self._serialize_engine_output(result.consensus.paddle_output)
            job.surya_output = self._serialize_engine_output(result.consensus.surya_output)
            job.consensus_output = self._serialize_engine_output(result.consensus.final_output)
            job.processing_time_ms = result.consensus.final_output.processing_time_ms

        if result.knowledge_document:
            from backend.services.document_intelligence.knowledge_builder import KnowledgeBuilder
            job.knowledge_document = KnowledgeBuilder().serialize_for_storage(result.knowledge_document)

        for pp in result.preprocessed_pages:
            page_num = pp.page_number
            paddle_text = ""
            surya_text = ""
            consensus_text = ""
            paddle_conf = surya_conf = consensus_conf = None

            if result.consensus:
                if result.consensus.paddle_output:
                    for p in result.consensus.paddle_output.pages:
                        if p.page_number == page_num:
                            paddle_text = p.full_text
                            paddle_conf = p.average_confidence
                if result.consensus.surya_output:
                    for p in result.consensus.surya_output.pages:
                        if p.page_number == page_num:
                            surya_text = p.full_text
                            surya_conf = p.average_confidence
                for p in result.consensus.final_output.pages:
                    if p.page_number == page_num:
                        consensus_text = p.full_text
                        consensus_conf = p.average_confidence

            page_regions = [
                {
                    "type": r.region_type,
                    "text": r.text[:500],
                    "confidence": r.confidence,
                    "bbox": r.bbox.to_list(),
                }
                for r in result.layout_regions
                if r.page_number == page_num
            ]

            self.db.add(OCRJobPage(
                tenant_id=job.tenant_id,
                job_id=job.id,
                page_number=page_num,
                original_image_path=pp.original_path,
                preprocessed_image_path=pp.processed_path,
                width=pp.width,
                height=pp.height,
                paddle_text=paddle_text,
                surya_text=surya_text,
                consensus_text=consensus_text,
                paddle_confidence=paddle_conf,
                surya_confidence=surya_conf,
                consensus_confidence=consensus_conf,
                layout_regions=page_regions,
                metadata_={"transforms": pp.transforms_applied},
            ))

        for field in result.fields:
            if field.field_name.startswith("line_"):
                continue
            self.db.add(OCRJobField(
                tenant_id=job.tenant_id,
                job_id=job.id,
                page_number=field.page_number,
                field_name=field.field_name,
                field_value=field.field_value,
                confidence=field.confidence,
                confidence_level=ConfidenceEngine()._to_level(field.confidence).value,
                source_engine=field.source_engine,
                paddle_value=next((a["value"] for a in field.alternatives if a.get("engine") == "paddleocr"), None),
                surya_value=next((a["value"] for a in field.alternatives if a.get("engine") == "surya"), None),
                bbox=field.bbox.to_list() if field.bbox else None,
                alternatives=field.alternatives,
            ))

        for table in result.tables:
            self.db.add(OCRJobTable(
                tenant_id=job.tenant_id,
                job_id=job.id,
                page_number=table.page_number,
                table_type=table.table_type,
                headers=table.headers,
                rows=table.rows,
                confidence=table.confidence,
                confidence_level=ConfidenceEngine()._to_level(table.confidence).value,
                extraction_method=table.extraction_method,
                bbox=table.bbox.to_list() if table.bbox else None,
                raw_data=table.raw_data,
            ))

        if result.validation:
            self.db.add(OCRValidationResult(
                tenant_id=job.tenant_id,
                job_id=job.id,
                is_valid=result.validation.is_valid,
                issues=[{"code": i.code, "severity": i.severity, "message": i.message, "field": i.field_name} for i in result.validation.issues],
                checks_passed=result.validation.checks_passed,
                checks_failed=result.validation.checks_failed,
                report={"is_valid": result.validation.is_valid},
            ))

        if result.confidence:
            for score_type, score, level in [
                ("document", result.confidence.document, result.confidence.document_level),
                ("ocr", result.confidence.ocr, result.confidence.ocr_level),
                ("field", result.confidence.field, result.confidence.field_level),
                ("table", result.confidence.table, result.confidence.table_level),
            ]:
                self.db.add(OCRConfidenceScore(
                    tenant_id=job.tenant_id,
                    job_id=job.id,
                    score_type=score_type,
                    score=score,
                    level=level.value,
                    details=result.confidence.per_field if score_type == "field" else {},
                ))

        await self._persist_stage_logs(job, stage_logs)

        document.status = DocumentStatus.PROCESSED
        document.processed_at = datetime.now(UTC)
        if result.classification:
            document.document_type = result.classification.document_class.value

        if result.knowledge_document:
            await self._index_knowledge(job, result)

        await self.db.flush()

    async def _index_knowledge(self, job: OCRJob, result: PipelineResult) -> None:
        try:
            from backend.services.knowledge.knowledge_orchestrator import KnowledgeOrchestrator

            kd = result.knowledge_document
            ocr_payload = {
                "title": kd.title,
                "document_class": kd.document_class,
                "metadata": kd.metadata,
                "raw_text": kd.raw_text,
                "structured_content": kd.structured_content,
                "fields": kd.fields,
                "tables": kd.tables,
            }
            orchestrator = KnowledgeOrchestrator(self.db)
            knowledge_doc = await orchestrator.index_from_ocr(job.tenant_id, ocr_payload, job.created_by)
            job.metadata_ = {**job.metadata_, "knowledge_document_id": str(knowledge_doc.id)}
        except Exception as exc:
            logger.warning("knowledge_indexing_failed", error=str(exc))

    async def _persist_stage_logs(self, job: OCRJob, stage_logs: list[StageLog]) -> None:
        for log in stage_logs:
            self.db.add(OCRPipelineStage(
                tenant_id=job.tenant_id,
                job_id=job.id,
                stage_name=log.stage.value,
                status=log.status,
                started_at=log.started_at,
                completed_at=log.completed_at,
                duration_ms=log.duration_ms,
                error_message=log.error,
                metadata_=log.metadata,
            ))

    def _serialize_engine_output(self, output) -> dict:
        if output is None:
            return {}
        return {
            "engine": output.engine_name,
            "processing_time_ms": output.processing_time_ms,
            "pages": [
                {
                    "page_number": p.page_number,
                    "full_text": p.full_text,
                    "confidence": p.average_confidence,
                    "token_count": len(p.tokens),
                }
                for p in output.pages
            ],
        }
