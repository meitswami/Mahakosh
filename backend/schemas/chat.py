from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    session_id: UUID | None = None
    chat_type: str | None = None
    stream: bool = False


class CitationResponse(BaseModel):
    source_document: str
    document_id: str = ""
    chunk_id: str = ""
    page_number: int | None = None
    confidence: float = 0
    confidence_display: str = ""
    excerpt: str = ""
    citation_text: str = ""


class ReasoningStepResponse(BaseModel):
    step_type: str
    label: str
    detail: str
    status: str = "completed"
    metadata: dict = Field(default_factory=dict)


class TransparencyAgent(BaseModel):
    name: str
    role: str
    description: str = ""
    confidence: float | None = None
    success: bool | None = None


class TransparencyDocument(BaseModel):
    document_id: str
    title: str
    document_type: str | None = None
    chunks_used: int = 0


class TransparencyChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str = ""
    page_number: int | None = None
    confidence: float = 0
    excerpt: str = ""
    rank: int = 0


class TransparencyResponse(BaseModel):
    agents_participated: list[TransparencyAgent] = Field(default_factory=list)
    documents_consulted: list[TransparencyDocument] = Field(default_factory=list)
    chunks_retrieved: list[TransparencyChunk] = Field(default_factory=list)
    confidence_score: float = 0
    confidence_level: str = "needs_review"
    confidence_display: str = "0%"
    sources: list[CitationResponse] = Field(default_factory=list)
    reasoning_path: list[ReasoningStepResponse] = Field(default_factory=list)
    knowledge_query_id: str | None = None
    model_used: str | None = None
    processing_time_ms: int = 0
    summary: str = ""


class ChatQueryResponse(BaseModel):
    answer: str
    session_id: str
    message_id: str | None = None
    chat_type: str
    intent: str
    confidence: float
    citations: list[CitationResponse] = Field(default_factory=list)
    structured_data: dict = Field(default_factory=dict)
    agents_used: list[str] = Field(default_factory=list)
    reasoning_steps: list[ReasoningStepResponse] = Field(default_factory=list)
    transparency: TransparencyResponse | None = None
    query_id: str | None = None
    processing_time_ms: int = 0
    model_used: str | None = None


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    chat_type: str
    message_count: int
    last_message_at: str | None
    created_at: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    chat_type: str | None = None
    intent: str | None = None
    confidence: float | None = None
    citations: list = Field(default_factory=list)
    structured_data: dict = Field(default_factory=dict)
    agents_used: list = Field(default_factory=list)
    reasoning_steps: list = Field(default_factory=list)
    transparency: dict | None = None
    created_at: str


class ChatSessionDetail(BaseModel):
    id: str
    title: str
    chat_type: str
    messages: list[ChatMessageResponse]


class ChatHistoryResponse(BaseModel):
    sessions: list[ChatSessionSummary]
    total: int


class SavedQueryRequest(BaseModel):
    name: str
    query_text: str
    chat_type: str = "general"
    filters: dict = Field(default_factory=dict)
