import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

import structlog

from backend.services.document_intelligence.confidence_engine import ConfidenceEngine
from backend.services.document_intelligence.consensus_engine import ConsensusEngine
from backend.services.document_intelligence.document_classifier import DocumentClassifier
from backend.services.document_intelligence.document_loader import DocumentLoader
from backend.services.document_intelligence.document_validator import DocumentValidator
from backend.services.document_intelligence.field_extractor import FieldExtractor
from backend.services.document_intelligence.image_preprocessor import ImagePreprocessor
from backend.services.document_intelligence.knowledge_builder import KnowledgeBuilder
from backend.services.document_intelligence.layout_analyzer import LayoutAnalyzer
from backend.services.document_intelligence.ocr_engine import ocr_engine_registry
from backend.services.document_intelligence.ocr_validation_agent import OCRValidationAgent
from backend.services.document_intelligence.table_extractor import TableExtractor
from backend.services.document_intelligence.types import (
    OCRJobStatus,
    PipelineResult,
    PipelineStage,
    StageLog,
)

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """End-to-end document intelligence pipeline for Indian business documents."""

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        os.makedirs(work_dir, exist_ok=True)
        self.classifier = DocumentClassifier()
        self.preprocessor = ImagePreprocessor()
        self.layout_analyzer = LayoutAnalyzer()
        self.table_extractor = TableExtractor()
        self.field_extractor = FieldExtractor()
        self.validator = DocumentValidator()
        self.confidence_engine = ConfidenceEngine()
        self.knowledge_builder = KnowledgeBuilder()
        self.consensus_engine = ConsensusEngine()
        self.ocr_validation_agent = OCRValidationAgent()
        self.stage_logs: list[StageLog] = []

    def run(
        self,
        file_path: str,
        document_id: UUID,
        job_id: UUID,
        language: str = "en+hi",
        title: str = "Document",
        metadata: dict[str, Any] | None = None,
        on_stage_complete: Callable[[StageLog], None] | None = None,
    ) -> PipelineResult:
        self.stage_logs = []
        pipeline_start = time.perf_counter()
        meta = metadata or {}

        pages_dir = str(Path(self.work_dir) / "pages")
        preprocessed_dir = str(Path(self.work_dir) / "preprocessed")
        os.makedirs(pages_dir, exist_ok=True)
        os.makedirs(preprocessed_dir, exist_ok=True)

        loader = DocumentLoader(pages_dir)

        with self._stage(PipelineStage.UPLOAD, on_stage_complete) as stage:
            page_paths = loader.load_pages(file_path)
            stage.metadata = {"page_count": len(page_paths), "file_path": file_path}

        preprocessed_pages = []
        with self._stage(PipelineStage.PREPROCESSING, on_stage_complete) as stage:
            for page_num, page_path in enumerate(page_paths, start=1):
                pp = self.preprocessor.preprocess_page(page_path, preprocessed_dir, page_num)
                preprocessed_pages.append(pp)
            ocr_input_paths = [p.processed_path for p in preprocessed_pages]
            stage.metadata = {"transforms": [p.transforms_applied for p in preprocessed_pages]}

        paddle_output = None
        with self._stage(PipelineStage.OCR_PADDLE, on_stage_complete) as stage:
            paddle_engine = ocr_engine_registry.get("paddleocr")
            paddle_output = paddle_engine.extract(ocr_input_paths, language)
            stage.metadata = {"processing_time_ms": paddle_output.processing_time_ms, "pages": len(paddle_output.pages)}

        surya_output = None
        with self._stage(PipelineStage.OCR_SURYA, on_stage_complete) as stage:
            surya_engine = ocr_engine_registry.get("surya")
            surya_output = surya_engine.extract(ocr_input_paths, language)
            stage.metadata = {"processing_time_ms": surya_output.processing_time_ms, "pages": len(surya_output.pages)}

        field_comparisons: dict[str, Any] = {}
        with self._stage(PipelineStage.OCR_CONSENSUS, on_stage_complete) as stage:
            validation_result = self.ocr_validation_agent.compare_outputs(paddle_output, surya_output)
            field_comparisons = validation_result.get("field_comparisons", {})
            consensus = self.consensus_engine.build_consensus(
                paddle_output, surya_output, field_comparisons
            )
            stage.metadata = {
                "consensus_confidence": consensus.consensus_confidence,
                "differences": len(consensus.field_differences),
                "text_similarity": validation_result.get("text_similarity"),
            }

        classification = None
        with self._stage(PipelineStage.CLASSIFICATION, on_stage_complete) as stage:
            classification = self.classifier.classify(
                consensus.final_output.full_text,
                {**meta, "file_name": Path(file_path).name},
            )
            stage.metadata = {
                "document_class": classification.document_class.value,
                "confidence": classification.confidence,
            }

        layout_regions = []
        with self._stage(PipelineStage.LAYOUT_ANALYSIS, on_stage_complete) as stage:
            layout_regions = self.layout_analyzer.analyze(consensus.final_output)
            stage.metadata = {"regions_found": len(layout_regions)}

        tables = []
        with self._stage(PipelineStage.TABLE_EXTRACTION, on_stage_complete) as stage:
            if Path(file_path).suffix.lower() == ".pdf":
                tables.extend(self.table_extractor.extract_from_pdf(file_path))
            tables.extend(self.table_extractor.extract_from_layout(layout_regions, {}))
            stage.metadata = {"tables_found": len(tables)}

        fields = []
        with self._stage(PipelineStage.FIELD_EXTRACTION, on_stage_complete) as stage:
            fields = self.field_extractor.extract(consensus, layout_regions, tables, field_comparisons)
            stage.metadata = {"fields_extracted": len(fields)}

        validation = None
        with self._stage(PipelineStage.VALIDATION, on_stage_complete) as stage:
            validation = self.validator.validate(fields, tables)
            stage.metadata = {
                "is_valid": validation.is_valid,
                "issues": len(validation.issues),
            }

        confidence = None
        with self._stage(PipelineStage.CONFIDENCE_SCORING, on_stage_complete) as stage:
            confidence = self.confidence_engine.calculate(
                classification, consensus, fields, tables, validation
            )
            stage.metadata = {
                "document_level": confidence.document_level.value,
                "ocr_level": confidence.ocr_level.value,
            }

        knowledge_document = None
        with self._stage(PipelineStage.KNOWLEDGE_BUILDING, on_stage_complete) as stage:
            knowledge_document = self.knowledge_builder.build(
                document_id=document_id,
                job_id=job_id,
                title=title,
                classification=classification,
                consensus=consensus,
                fields=fields,
                tables=tables,
                confidence=confidence,
                validation=validation,
            )
            stage.metadata = {"embedding_text_length": len(knowledge_document.embedding_text)}

        with self._stage(PipelineStage.STORAGE, on_stage_complete) as stage:
            stage.metadata = {"status": "ready_for_persistence"}

        total_ms = int((time.perf_counter() - pipeline_start) * 1000)
        logger.info("pipeline_completed", job_id=str(job_id), duration_ms=total_ms)

        return PipelineResult(
            job_id=job_id,
            document_id=document_id,
            status=OCRJobStatus.COMPLETED,
            classification=classification,
            consensus=consensus,
            layout_regions=layout_regions,
            tables=tables,
            fields=fields,
            validation=validation,
            confidence=confidence,
            knowledge_document=knowledge_document,
            stage_logs=self.stage_logs,
            preprocessed_pages=preprocessed_pages,
        )

    def _stage(
        self,
        stage: PipelineStage,
        callback: Callable[[StageLog], None] | None,
    ):
        return _StageContext(self, stage, callback)


class _StageContext:
    def __init__(
        self,
        orchestrator: PipelineOrchestrator,
        stage: PipelineStage,
        callback: Callable[[StageLog], None] | None,
    ):
        self.orchestrator = orchestrator
        self.stage = stage
        self.callback = callback
        self.log = StageLog(stage=stage, status="running", started_at=datetime.now(UTC))
        self.log.metadata = {}

    def __enter__(self) -> StageLog:
        logger.info("pipeline_stage_started", stage=self.stage.value)
        return self.log

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log.completed_at = datetime.now(UTC)
        self.log.duration_ms = int((self.log.completed_at - self.log.started_at).total_seconds() * 1000)

        if exc_type is not None:
            self.log.status = "failed"
            self.log.error = str(exc_val)
            logger.error("pipeline_stage_failed", stage=self.stage.value, error=str(exc_val))
        else:
            self.log.status = "completed"
            logger.info("pipeline_stage_completed", stage=self.stage.value, duration_ms=self.log.duration_ms)

        self.orchestrator.stage_logs.append(self.log)
        if self.callback:
            self.callback(self.log)
        return False
