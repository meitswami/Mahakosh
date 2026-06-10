from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeIndexRequest(BaseModel):
    title: str | None = None
    text: str | None = None
    document_type: str = "general"
    structured_fields: dict = Field(default_factory=dict)
    tables: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    ocr_job_id: UUID | None = None
    collection_slug: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    mode: str = "hybrid"
    top_k: int = Field(default=20, ge=1, le=100)
    filters: dict | None = None
    collection_slug: str | None = None
    rerank: bool = True


class KnowledgeCitationResponse(BaseModel):
    source_document: str
    document_id: str
    chunk_id: str
    page_number: int | None
    confidence: float
    confidence_display: str
    rank: int
    excerpt: str
    citation_text: str


class KnowledgeSearchResultItem(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    document_title: str
    document_type: str
    source_name: str
    page_number: int | None
    metadata: dict = Field(default_factory=dict)
    citation: KnowledgeCitationResponse | None = None


class KnowledgeSearchResponse(BaseModel):
    query_id: UUID | None
    query: str
    mode: str
    results: list[KnowledgeSearchResultItem]
    citations: list[KnowledgeCitationResponse]
    processing_time_ms: int
    total_found: int


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    title: str
    document_type: str
    source: str
    index_status: str
    chunk_count: int
    confidence: float | None
    vendor_name: str | None
    customer_name: str | None
    gstin: str | None
    invoice_number: str | None
    document_date: str | None
    amount: float | None
    tags: list
    indexed_at: datetime | None
    created_at: datetime
    structured_fields: dict = Field(default_factory=dict)
    tables: list = Field(default_factory=list)

    model_config = {"from_attributes": True}


class KnowledgeChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    token_count: int
    chunk_type: str
    page_number: int | None
    metadata: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class KnowledgeCollectionResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    collection_type: str
    document_count: int
    chunk_count: int

    model_config = {"from_attributes": True}


class KnowledgeOverviewResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_queries: int
    collections: list[KnowledgeCollectionResponse]
    top_sources: list[dict]
    recent_queries: list[dict]


class KnowledgeGraphResponse(BaseModel):
    document_id: UUID
    nodes: list[dict]
    edges: list[dict]
