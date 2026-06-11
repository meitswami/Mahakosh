"""Bridge accounting knowledge objects to the knowledge base."""

from __future__ import annotations

from typing import Any
from uuid import UUID


ACCOUNTING_KNOWLEDGE_TYPES = (
    "ledger_mapping",
    "item_mapping",
    "voucher_pattern",
    "gst_rule",
    "tally_export",
    "connector_config",
)


def ledger_mapping_to_knowledge(mapping: dict[str, Any], connector_name: str) -> dict[str, Any]:
    return {
        "title": f"Ledger mapping: {mapping.get('external_name')} → {mapping.get('target_name', 'unmapped')}",
        "content": (
            f"External ledger '{mapping.get('external_name')}' maps to "
            f"'{mapping.get('target_name')}' via {mapping.get('match_type')} match "
            f"(confidence: {mapping.get('confidence')}%). "
            f"Reasoning: {mapping.get('reasoning', 'N/A')}. "
            f"Connector: {connector_name}."
        ),
        "document_type": "ledger_mapping",
        "tags": ["accounting", "ledger", "mapping", connector_name],
        "metadata": mapping,
    }


def voucher_pattern_to_knowledge(voucher: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": f"Voucher pattern: {voucher.get('voucher_type')} — {voucher.get('party_name', 'N/A')}",
        "content": (
            f"{voucher.get('voucher_type', 'Unknown').title()} voucher for "
            f"₹{voucher.get('total_amount', 0):,.2f}. "
            f"GST: CGST ₹{voucher.get('cgst_amount', 0)}, SGST ₹{voucher.get('sgst_amount', 0)}, "
            f"IGST ₹{voucher.get('igst_amount', 0)}. "
            f"Lines: {len(voucher.get('lines', []))}."
        ),
        "document_type": "voucher_pattern",
        "tags": ["accounting", "voucher", voucher.get("voucher_type", "general")],
        "metadata": voucher,
    }


def gst_insight_to_knowledge(insight: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": f"GST liability: ₹{insight.get('net_liability', 0):,.2f}",
        "content": (
            f"Net GST liability ₹{insight.get('net_liability', 0):,.2f}. "
            f"Output tax: CGST ₹{insight.get('output_tax', {}).get('cgst', 0)}, "
            f"SGST ₹{insight.get('output_tax', {}).get('sgst', 0)}. "
            f"Input tax: CGST ₹{insight.get('input_tax', {}).get('cgst', 0)}, "
            f"SGST ₹{insight.get('input_tax', {}).get('sgst', 0)}."
        ),
        "document_type": "gst_rule",
        "tags": ["accounting", "gst", "liability"],
        "metadata": insight,
    }


async def ingest_accounting_knowledge(
    knowledge_tool: Any,
    tenant_id: UUID,
    user_id: UUID | None,
    objects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ingest accounting knowledge objects into the knowledge base via KnowledgeTool."""
    ingested = 0
    for obj in objects:
        doc_type = obj.get("document_type", "accounting")
        title = obj.get("title", "Accounting knowledge")
        content = obj.get("content", "")
        if hasattr(knowledge_tool, "ingest"):
            await knowledge_tool.ingest(
                tenant_id=tenant_id,
                title=title,
                content=content,
                document_type=doc_type,
                tags=obj.get("tags", ["accounting"]),
                metadata=obj.get("metadata", {}),
                user_id=user_id,
            )
            ingested += 1
    return {"ingested": ingested, "total": len(objects)}
