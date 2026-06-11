"""Bridge digital twin objects to the knowledge base for agent search."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.connectors.accounting.knowledge_bridge import ingest_accounting_knowledge


def twin_ledger_to_knowledge(obj: dict[str, Any]) -> dict[str, Any]:
    fields = obj.get("normalized_fields", obj)
    name = fields.get("name", obj.get("display_name", "Unknown"))
    balance = fields.get("current_balance", fields.get("opening_balance", 0))
    return {
        "title": f"Ledger: {name}",
        "content": (
            f"Normalized ledger '{name}' in group '{fields.get('parent_group', 'N/A')}'. "
            f"Type: {fields.get('ledger_type', 'general')}. "
            f"Balance: ₹{balance:,.2f}. "
            f"GSTIN: {fields.get('gstin') or 'not set'}. "
            f"Quality score: {obj.get('quality_score', 'N/A')}/100. "
            f"Source: {obj.get('source_system', 'unknown')}."
        ),
        "document_type": "ledger_mapping",
        "tags": ["accounting", "twin", "ledger", fields.get("ledger_type", "general")],
        "metadata": obj,
    }


def twin_party_to_knowledge(obj: dict[str, Any]) -> dict[str, Any]:
    fields = obj.get("normalized_fields", obj)
    name = fields.get("name", obj.get("display_name", "Unknown"))
    party_type = fields.get("party_type", "party")
    return {
        "title": f"{party_type.title()}: {name}",
        "content": (
            f"Normalized {party_type} '{name}'. "
            f"GSTIN: {fields.get('gstin') or 'not set'}. "
            f"State: {fields.get('state') or 'unknown'}. "
            f"Quality score: {obj.get('quality_score', 'N/A')}/100."
        ),
        "document_type": "ledger_mapping",
        "tags": ["accounting", "twin", "party", party_type],
        "metadata": obj,
    }


def twin_item_to_knowledge(obj: dict[str, Any]) -> dict[str, Any]:
    fields = obj.get("normalized_fields", obj)
    name = fields.get("name", obj.get("display_name", "Unknown"))
    return {
        "title": f"Stock item: {name}",
        "content": (
            f"Normalized stock item '{name}'. "
            f"HSN: {fields.get('hsn_code') or 'missing'}. "
            f"GST rate: {fields.get('gst_rate', 'unknown')}%. "
            f"Unit: {fields.get('unit', 'NOS')}. "
            f"Quality score: {obj.get('quality_score', 'N/A')}/100."
        ),
        "document_type": "item_mapping",
        "tags": ["accounting", "twin", "stock_item"],
        "metadata": obj,
    }


def twin_voucher_to_knowledge(obj: dict[str, Any]) -> dict[str, Any]:
    fields = obj.get("normalized_fields", obj)
    return {
        "title": f"Voucher: {fields.get('voucher_type', 'unknown')} — {fields.get('party_name', 'N/A')}",
        "content": (
            f"{fields.get('voucher_type', 'Unknown').title()} voucher "
            f"#{fields.get('voucher_number', 'N/A')} dated {fields.get('voucher_date', 'N/A')}. "
            f"Party: {fields.get('party_name', 'N/A')}. "
            f"Total: ₹{fields.get('total_amount', 0):,.2f}. "
            f"GST: CGST ₹{fields.get('cgst_amount', 0)}, SGST ₹{fields.get('sgst_amount', 0)}, "
            f"IGST ₹{fields.get('igst_amount', 0)}."
        ),
        "document_type": "voucher_pattern",
        "tags": ["accounting", "twin", "voucher", fields.get("voucher_type", "general")],
        "metadata": obj,
    }


def twin_outstanding_to_knowledge(obj: dict[str, Any]) -> dict[str, Any]:
    fields = obj.get("normalized_fields", obj)
    outstanding_type = fields.get("outstanding_type", "receivable")
    return {
        "title": f"Outstanding {outstanding_type}: {fields.get('party_name', 'Unknown')}",
        "content": (
            f"{outstanding_type.title()} of ₹{fields.get('amount', 0):,.2f} "
            f"from {fields.get('party_name', 'Unknown')}. "
            f"Bill ref: {fields.get('bill_ref', 'N/A')}. "
            f"Due: {fields.get('due_date', 'N/A')}."
        ),
        "document_type": "voucher_pattern",
        "tags": ["accounting", "twin", "outstanding", outstanding_type],
        "metadata": obj,
    }


def twin_object_to_knowledge(obj: dict[str, Any]) -> dict[str, Any]:
    """Convert any twin object dict to a knowledge document."""
    obj_type = obj.get("object_type", "")
    converters = {
        "ledger": twin_ledger_to_knowledge,
        "ledger_group": twin_ledger_to_knowledge,
        "stock_item": twin_item_to_knowledge,
        "party": twin_party_to_knowledge,
        "voucher": twin_voucher_to_knowledge,
        "outstanding": twin_outstanding_to_knowledge,
    }
    converter = converters.get(obj_type)
    if converter:
        return converter(obj)
    name = obj.get("display_name", "Accounting object")
    return {
        "title": f"Twin object: {name}",
        "content": f"Normalized accounting object ({obj_type}). Quality: {obj.get('quality_score', 'N/A')}/100.",
        "document_type": "ledger_mapping",
        "tags": ["accounting", "twin", obj_type],
        "metadata": obj,
    }


def build_twin_summary_knowledge(overview: dict[str, Any]) -> dict[str, Any]:
    """Build a summary knowledge chunk for twin overview queries."""
    counts = overview.get("object_counts", {})
    return {
        "title": "Accounting Digital Twin Overview",
        "content": (
            f"Digital twin contains {overview.get('total_objects', 0)} normalized objects. "
            f"Average quality score: {overview.get('avg_quality_score', 0)}/100. "
            f"Open data issues: {overview.get('open_issues', 0)} "
            f"({overview.get('error_issues', 0)} errors). "
            f"Breakdown: {', '.join(f'{k}: {v}' for k, v in counts.items())}."
        ),
        "document_type": "ledger_mapping",
        "tags": ["accounting", "twin", "overview"],
        "metadata": overview,
    }


async def ingest_twin_knowledge(
    knowledge_tool: Any,
    tenant_id: UUID,
    user_id: UUID | None,
    objects: list[dict[str, Any]],
    overview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest twin objects into knowledge base for agent search."""
    docs = [twin_object_to_knowledge(obj) for obj in objects]
    if overview:
        docs.append(build_twin_summary_knowledge(overview))
    return await ingest_accounting_knowledge(knowledge_tool, tenant_id, user_id, docs)
