from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import PaginatedResponse, TimestampSchema


class OCRUploadResponse(BaseModel):
    job_id: UUID
    document_id: UUID
    status: str
    file_name: str
    message: str


class OCRProcessRequest(BaseModel):
    job_id: UUID
    language: str = "en+hi"


class OCRJobStatusResponse(BaseModel):
    job_id: UUID
    document_id: UUID
    status: str
    document_class: str | None = None
    classification_confidence: float | None = None
    page_count: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    processing_time_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OCRPipelineStageResponse(BaseModel):
    stage_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class OCRFieldResponse(BaseModel):
    field_name: str
    field_value: str | None
    confidence: float
    confidence_level: str
    source_engine: str | None = None
    paddle_value: str | None = None
    surya_value: str | None = None


class OCRTableResponse(BaseModel):
    table_type: str
    page_number: int
    headers: list[str]
    rows: list[list[str]]
    confidence: float
    confidence_level: str
    extraction_method: str


class OCRPageResponse(BaseModel):
    page_number: int
    consensus_text: str | None = None
    consensus_confidence: float | None = None
    paddle_confidence: float | None = None
    surya_confidence: float | None = None
    preprocessed_image_path: str | None = None


class OCRConfidenceResponse(BaseModel):
    score_type: str
    score: float
    level: str


class OCRValidationResponse(BaseModel):
    job_id: UUID
    is_valid: bool
    issues: list[dict]
    checks_passed: list[str]
    checks_failed: list[str]


class OCRResultResponse(BaseModel):
    job_id: UUID
    document_id: UUID
    status: str
    document_class: str | None = None
    classification_confidence: float | None = None
    paddle_output: dict = Field(default_factory=dict)
    surya_output: dict = Field(default_factory=dict)
    consensus_output: dict = Field(default_factory=dict)
    fields: list[OCRFieldResponse] = Field(default_factory=list)
    tables: list[OCRTableResponse] = Field(default_factory=list)
    pages: list[OCRPageResponse] = Field(default_factory=list)
    confidence_scores: list[OCRConfidenceResponse] = Field(default_factory=list)
    pipeline_stages: list[OCRPipelineStageResponse] = Field(default_factory=list)
    knowledge_document: dict = Field(default_factory=dict)


class OCRJobListResponse(PaginatedResponse[OCRJobStatusResponse]):
    pass
