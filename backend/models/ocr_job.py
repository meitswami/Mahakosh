import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OCRJobStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OCRJob(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default=OCRJobStatus.PENDING, nullable=False, index=True)
    document_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="en+hi", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paddle_output: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    surya_output: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    consensus_output: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    knowledge_document: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    pages = relationship("OCRJobPage", back_populates="job", cascade="all, delete-orphan")
    fields = relationship("OCRJobField", back_populates="job", cascade="all, delete-orphan")
    tables = relationship("OCRJobTable", back_populates="job", cascade="all, delete-orphan")
    validation_results = relationship("OCRValidationResult", back_populates="job", cascade="all, delete-orphan")
    confidence_scores = relationship("OCRConfidenceScore", back_populates="job", cascade="all, delete-orphan")
    pipeline_stages = relationship("OCRPipelineStage", back_populates="job", cascade="all, delete-orphan")


class OCRJobPage(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_pages"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_image_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    preprocessed_image_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paddle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    surya_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    consensus_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    paddle_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    surya_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    consensus_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    layout_regions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    job = relationship("OCRJob", back_populates="pages")


class OCRJobField(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_fields"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    source_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    paddle_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    surya_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    alternatives: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    job = relationship("OCRJob", back_populates="fields")


class OCRJobTable(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_tables"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    table_type: Mapped[str] = mapped_column(String(100), nullable=False)
    headers: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    rows: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    job = relationship("OCRJob", back_populates="tables")


class OCRValidationResult(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_validation_results"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_valid: Mapped[bool] = mapped_column(default=False, nullable=False)
    issues: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    checks_passed: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    checks_failed: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    report: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    job = relationship("OCRJob", back_populates="validation_results")


class OCRConfidenceScore(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_confidence_scores"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    job = relationship("OCRJob", back_populates="confidence_scores")


class OCRPipelineStage(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ocr_pipeline_stages"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    job = relationship("OCRJob", back_populates="pipeline_stages")
