from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class DocumentClass(StrEnum):
    INVOICE = "invoice"
    PURCHASE_INVOICE = "purchase_invoice"
    SALES_INVOICE = "sales_invoice"
    GST_INVOICE = "gst_invoice"
    DELIVERY_CHALLAN = "delivery_challan"
    QUOTATION = "quotation"
    BANK_STATEMENT = "bank_statement"
    LEDGER = "ledger"
    PURCHASE_ORDER = "purchase_order"
    UNKNOWN = "unknown"


class OCRJobStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PipelineStage(StrEnum):
    UPLOAD = "upload"
    CLASSIFICATION = "classification"
    PREPROCESSING = "preprocessing"
    OCR_PADDLE = "ocr_paddle"
    OCR_SURYA = "ocr_surya"
    OCR_CONSENSUS = "ocr_consensus"
    LAYOUT_ANALYSIS = "layout_analysis"
    TABLE_EXTRACTION = "table_extraction"
    FIELD_EXTRACTION = "field_extraction"
    VALIDATION = "validation"
    CONFIDENCE_SCORING = "confidence_scoring"
    KNOWLEDGE_BUILDING = "knowledge_building"
    STORAGE = "storage"


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def to_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


@dataclass
class OCRToken:
    text: str
    confidence: float
    bbox: BoundingBox
    line_id: int | None = None


@dataclass
class OCRPageOutput:
    page_number: int
    width: int
    height: int
    tokens: list[OCRToken] = field(default_factory=list)
    full_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def average_confidence(self) -> float:
        if not self.tokens:
            return 0.0
        return sum(t.confidence for t in self.tokens) / len(self.tokens)


@dataclass
class OCREngineOutput:
    engine_name: str
    pages: list[OCRPageOutput]
    processing_time_ms: int
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.full_text for p in self.pages)


@dataclass
class ClassificationResult:
    document_class: DocumentClass
    confidence: float
    signals: dict[str, float] = field(default_factory=dict)


@dataclass
class PreprocessedPage:
    page_number: int
    original_path: str
    processed_path: str
    width: int
    height: int
    transforms_applied: list[str] = field(default_factory=list)


@dataclass
class LayoutRegion:
    region_type: str
    bbox: BoundingBox
    text: str
    confidence: float
    page_number: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTable:
    table_id: str
    table_type: str
    page_number: int
    headers: list[str]
    rows: list[list[str]]
    bbox: BoundingBox | None = None
    confidence: float = 0.0
    extraction_method: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedField:
    field_name: str
    field_value: str | None
    confidence: float
    source_engine: str | None = None
    bbox: BoundingBox | None = None
    page_number: int | None = None
    alternatives: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationIssue:
    code: str
    severity: str
    message: str
    field_name: str | None = None


@dataclass
class ValidationReport:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)


@dataclass
class ConfidenceScores:
    document: float
    document_level: ConfidenceLevel
    ocr: float
    ocr_level: ConfidenceLevel
    field: float
    field_level: ConfidenceLevel
    table: float
    table_level: ConfidenceLevel
    per_field: dict[str, float] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    final_output: OCREngineOutput
    paddle_output: OCREngineOutput | None
    surya_output: OCREngineOutput | None
    field_differences: list[dict[str, Any]] = field(default_factory=list)
    selected_engine_per_field: dict[str, str] = field(default_factory=dict)
    consensus_confidence: float = 0.0


@dataclass
class KnowledgeDocument:
    document_id: UUID | None
    job_id: UUID | None
    title: str
    document_class: str
    metadata: dict[str, Any]
    raw_text: str
    structured_content: dict[str, Any]
    embedding_text: str
    fields: dict[str, Any]
    tables: list[dict[str, Any]]


@dataclass
class StageLog:
    stage: PipelineStage
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    job_id: UUID
    document_id: UUID
    status: OCRJobStatus
    classification: ClassificationResult | None
    consensus: ConsensusResult | None
    layout_regions: list[LayoutRegion]
    tables: list[ExtractedTable]
    fields: list[ExtractedField]
    validation: ValidationReport | None
    confidence: ConfidenceScores | None
    knowledge_document: KnowledgeDocument | None
    stage_logs: list[StageLog] = field(default_factory=list)
    preprocessed_pages: list[PreprocessedPage] = field(default_factory=list)
