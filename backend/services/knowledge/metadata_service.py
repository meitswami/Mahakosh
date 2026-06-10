import re
from typing import Any

from backend.services.knowledge.types import KnowledgeObject, QdrantCollectionType


class MetadataService:
    """Extracts and normalizes metadata for knowledge objects."""

    GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", re.I)
    AMOUNT_RE = re.compile(r"(?:rs\.?|₹|inr)?\s*([\d,]+\.?\d*)", re.I)

    COLLECTION_MAP: dict[str, str] = {
        "invoice": QdrantCollectionType.INVOICES.value,
        "purchase_invoice": QdrantCollectionType.INVOICES.value,
        "sales_invoice": QdrantCollectionType.INVOICES.value,
        "gst_invoice": QdrantCollectionType.INVOICES.value,
        "vendor": QdrantCollectionType.VENDORS.value,
        "customer": QdrantCollectionType.CUSTOMERS.value,
        "general": QdrantCollectionType.DOCUMENTS.value,
    }

    def extract_from_object(self, obj: KnowledgeObject) -> dict[str, Any]:
        fields = obj.structured_fields or {}
        meta = {
            "title": obj.title,
            "document_type": obj.document_type,
            "source": obj.source,
            "vendor_name": fields.get("vendor_name"),
            "customer_name": fields.get("customer_name"),
            "gstin": fields.get("gstin") or fields.get("vendor_gstin"),
            "invoice_number": fields.get("invoice_number"),
            "document_date": fields.get("invoice_date"),
            "amount": self._parse_amount(fields.get("grand_total")),
            "confidence": obj.confidence,
            "tags": obj.tags,
            "workflow_id": obj.metadata.get("workflow_id"),
            "ocr_job_id": obj.metadata.get("job_id"),
            "collection_slug": self.resolve_collection_slug(obj.document_type, obj.collection_slug),
        }
        meta.update({k: v for k, v in obj.metadata.items() if k not in meta})
        return meta

    def resolve_collection_slug(self, document_type: str, override: str | None = None) -> str:
        if override and override != "general":
            return override
        return self.COLLECTION_MAP.get(document_type, QdrantCollectionType.KNOWLEDGE.value)

    def build_qdrant_payload(
        self,
        tenant_id: str,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
        content: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "document_id": document_id,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "content": content[:2000],
            "document_type": metadata.get("document_type"),
            "title": metadata.get("title"),
            "source": metadata.get("source"),
            "vendor_name": metadata.get("vendor_name"),
            "customer_name": metadata.get("customer_name"),
            "gstin": metadata.get("gstin"),
            "invoice_number": metadata.get("invoice_number"),
            "document_date": metadata.get("document_date"),
            "amount": metadata.get("amount"),
            "page_number": metadata.get("page_number"),
            "confidence": metadata.get("confidence"),
            "tags": metadata.get("tags", []),
        }

    def build_search_filters(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        if not filters:
            return {}
        allowed = {
            "document_type", "vendor_name", "customer_name", "gstin",
            "invoice_number", "document_id", "tenant_id",
        }
        return {k: v for k, v in filters.items() if k in allowed and v is not None}

    def _parse_amount(self, value: str | None) -> float | None:
        if not value:
            return None
        match = self.AMOUNT_RE.search(str(value))
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return None
        return None
