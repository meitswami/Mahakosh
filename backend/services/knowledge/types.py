from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class ChunkStrategy(StrEnum):
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    TABLE_AWARE = "table_aware"
    DOCUMENT_AWARE = "document_aware"


class SearchMode(StrEnum):
    KEYWORD = "keyword"
    VECTOR = "vector"
    METADATA = "metadata"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"


class QdrantCollectionType(StrEnum):
    DOCUMENTS = "documents"
    INVOICES = "invoices"
    VENDORS = "vendors"
    CUSTOMERS = "customers"
    KNOWLEDGE = "knowledge"
    CHAT_MEMORY = "chat_memory"
    WORKFLOW_MEMORY = "workflow_memory"


class GraphNodeType(StrEnum):
    VENDOR = "Vendor"
    CUSTOMER = "Customer"
    ITEM = "Item"
    INVOICE = "Invoice"
    LEDGER = "Ledger"
    VOUCHER = "Voucher"
    DOCUMENT = "Document"


class GraphRelationshipType(StrEnum):
    CONTAINS = "Contains"
    REFERENCES = "References"
    PURCHASED = "Purchased"
    SOLD = "Sold"
    LINKED = "Linked"


@dataclass
class KnowledgeObject:
    document_id: UUID | None
    title: str
    document_type: str
    source: str
    metadata: dict[str, Any]
    raw_text: str
    structured_fields: dict[str, Any]
    tables: list[dict[str, Any]]
    relationships: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    confidence: float | None = None
    collection_slug: str = "general"


@dataclass
class ChunkResult:
    chunk_index: int
    content: str
    token_count: int
    chunk_type: str
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    document_title: str
    document_type: str
    source_name: str
    page_number: int | None
    metadata: dict[str, Any] = field(default_factory=dict)
    citation: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    query_id: UUID | None
    query: str
    mode: str
    results: list[RetrievalResult]
    citations: list[dict[str, Any]]
    processing_time_ms: int
    total_found: int
