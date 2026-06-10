import json
from uuid import UUID

from backend.services.document_intelligence.types import (
    ClassificationResult,
    ConfidenceScores,
    ConsensusResult,
    ExtractedField,
    ExtractedTable,
    KnowledgeDocument,
    ValidationReport,
)


class KnowledgeBuilder:
    """Converts OCR pipeline output into embedding-ready knowledge documents."""

    def build(
        self,
        document_id: UUID | None,
        job_id: UUID | None,
        title: str,
        classification: ClassificationResult,
        consensus: ConsensusResult,
        fields: list[ExtractedField],
        tables: list[ExtractedTable],
        confidence: ConfidenceScores,
        validation: ValidationReport,
    ) -> KnowledgeDocument:
        field_dict = {f.field_name: f.field_value for f in fields if f.field_value}
        table_data = [
            {
                "table_type": t.table_type,
                "page": t.page_number,
                "headers": t.headers,
                "rows": t.rows[:50],
                "confidence": t.confidence,
            }
            for t in tables
        ]

        structured_content = {
            "document_class": classification.document_class.value,
            "classification_confidence": classification.confidence,
            "fields": field_dict,
            "tables": table_data,
            "validation": {
                "is_valid": validation.is_valid,
                "issues_count": len(validation.issues),
                "checks_passed": validation.checks_passed,
                "checks_failed": validation.checks_failed,
            },
            "confidence": {
                "document": confidence.document,
                "ocr": confidence.ocr,
                "field": confidence.field,
                "table": confidence.table,
                "levels": {
                    "document": confidence.document_level.value,
                    "ocr": confidence.ocr_level.value,
                    "field": confidence.field_level.value,
                    "table": confidence.table_level.value,
                },
            },
            "ocr_engines": {
                "paddle": consensus.paddle_output is not None,
                "surya": consensus.surya_output is not None,
                "consensus_confidence": consensus.consensus_confidence,
                "differences_count": len(consensus.field_differences),
            },
        }

        embedding_text = self._build_embedding_text(title, classification, field_dict, consensus.final_output.full_text)

        metadata = {
            "source": "mahakosh_ocr_pipeline",
            "document_id": str(document_id) if document_id else None,
            "job_id": str(job_id) if job_id else None,
            "page_count": len(consensus.final_output.pages),
            "language": "en+hi",
        }

        return KnowledgeDocument(
            document_id=document_id,
            job_id=job_id,
            title=title,
            document_class=classification.document_class.value,
            metadata=metadata,
            raw_text=consensus.final_output.full_text,
            structured_content=structured_content,
            embedding_text=embedding_text,
            fields=field_dict,
            tables=table_data,
        )

    def _build_embedding_text(
        self,
        title: str,
        classification: ClassificationResult,
        fields: dict,
        raw_text: str,
    ) -> str:
        parts = [
            f"Title: {title}",
            f"Document Type: {classification.document_class.value}",
        ]

        key_fields = ["invoice_number", "invoice_date", "vendor_name", "customer_name", "gstin", "grand_total"]
        for key in key_fields:
            if key in fields and fields[key]:
                parts.append(f"{key.replace('_', ' ').title()}: {fields[key]}")

        text_summary = raw_text[:3000] if len(raw_text) > 3000 else raw_text
        parts.append(f"Content:\n{text_summary}")

        return "\n".join(parts)

    def serialize_for_storage(self, knowledge: KnowledgeDocument) -> dict:
        return {
            "title": knowledge.title,
            "document_class": knowledge.document_class,
            "metadata": knowledge.metadata,
            "raw_text": knowledge.raw_text,
            "structured_content": knowledge.structured_content,
            "embedding_text": knowledge.embedding_text,
            "fields": knowledge.fields,
            "tables": knowledge.tables,
        }
