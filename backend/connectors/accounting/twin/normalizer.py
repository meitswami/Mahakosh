"""Normalization engine — raw ERP data → clean digital twin objects."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.connectors.accounting.base.types import ImportEntityType
from backend.connectors.accounting.mapping.mapping_engine import MappingEngine
from backend.connectors.accounting.twin.objects import (
    IssueSeverity,
    NormalizedLedger,
    NormalizedLedgerGroup,
    NormalizedOutstanding,
    NormalizedParty,
    NormalizedStockItem,
    NormalizedUnit,
    NormalizedVoucher,
    TwinObjectBase,
)
from backend.connectors.accounting.twin.reality import IndianAccountingReality


class AccountingNormalizer:
    """Clean, score, and normalize raw connector data into twin objects."""

    def __init__(self, aliases: dict[str, str] | None = None):
        self.aliases = aliases or {}
        self.reality = IndianAccountingReality()
        self._mapping_engine = MappingEngine()

    def normalize_import(
        self,
        entity_type: ImportEntityType,
        raw_data: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> list[TwinObjectBase]:
        """Convert raw connector import payload to normalized twin objects."""
        objects: list[TwinObjectBase] = []

        if entity_type == ImportEntityType.LEDGERS:
            for raw in raw_data.get("ledgers", []):
                obj = self.normalize_ledger(raw, source_system, connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type in (ImportEntityType.STOCK_ITEMS, ImportEntityType.INVENTORY):
            for raw in raw_data.get("items", []):
                obj = self.normalize_stock_item(raw, source_system, connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type == ImportEntityType.GROUPS:
            for raw in raw_data.get("groups", raw_data.get("ledgers", [])):
                obj = self.normalize_ledger_group(raw, source_system, connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type == ImportEntityType.UNITS:
            for raw in raw_data.get("units", []):
                obj = self.normalize_unit(raw, source_system, connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type == ImportEntityType.VOUCHERS:
            for raw in raw_data.get("vouchers", []):
                obj = self.normalize_voucher(raw, source_system, connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type == ImportEntityType.VENDORS:
            for raw in raw_data.get("ledgers", raw_data.get("vendors", [])):
                obj = self.normalize_party(raw, source_system, "vendor", connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type == ImportEntityType.CUSTOMERS:
            for raw in raw_data.get("ledgers", raw_data.get("customers", [])):
                obj = self.normalize_party(raw, source_system, "customer", connector_id, sync_job_id)
                objects.append(obj)
        elif entity_type == ImportEntityType.OUTSTANDING:
            for raw in raw_data.get("outstanding", raw_data.get("ledgers", [])):
                obj = self.normalize_outstanding(raw, source_system, connector_id, sync_job_id)
                objects.append(obj)

        return objects

    def normalize_ledger(
        self,
        raw: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedLedger:
        obj = NormalizedLedger.from_raw(raw, source_system)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        self.reality.apply_ledger_rules(obj, self.aliases)
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def normalize_ledger_group(
        self,
        raw: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedLedgerGroup:
        obj = NormalizedLedgerGroup.from_raw(raw, source_system)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        name = obj.normalized_fields.get("name", "")
        cleaned, notes = self.reality.clean_ledger_name(name)
        for note in notes:
            obj.add_note(note)
        if cleaned != name:
            obj.normalized_fields["original_name"] = name
            obj.normalized_fields["name"] = cleaned
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def normalize_stock_item(
        self,
        raw: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedStockItem:
        obj = NormalizedStockItem.from_raw(raw, source_system)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        self.reality.apply_item_rules(obj)
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def normalize_unit(
        self,
        raw: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedUnit:
        obj = NormalizedUnit.from_raw(raw, source_system)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def normalize_voucher(
        self,
        raw: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedVoucher:
        obj = NormalizedVoucher.from_raw(raw, source_system)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        self.reality.apply_voucher_rules(obj)
        for line in obj.lines:
            line.quality_score = self.reality.compute_quality_score(line)
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def normalize_party(
        self,
        raw: dict[str, Any],
        source_system: str,
        party_type: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedParty:
        obj = NormalizedParty.from_raw(raw, source_system, party_type)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        self.reality.apply_party_rules(obj)
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def normalize_outstanding(
        self,
        raw: dict[str, Any],
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> NormalizedOutstanding:
        obj = NormalizedOutstanding.from_raw(raw, source_system)
        obj.connector_id = connector_id
        obj.sync_job_id = sync_job_id
        if not obj.normalized_fields.get("party_name"):
            obj.add_issue(
                "missing_party",
                "Outstanding entry missing party name",
                severity=IssueSeverity.ERROR,
            )
        obj.quality_score = self.reality.compute_quality_score(obj)
        return obj

    def detect_duplicates(self, objects: list[TwinObjectBase]) -> list[dict[str, Any]]:
        """Detect duplicate twin objects via fuzzy + exact matching."""
        names = [obj.display_name for obj in objects if obj.display_name]
        dupes = self._mapping_engine.detect_duplicates(names)
        enriched = []
        for dupe in dupes:
            obj_a = next((o for o in objects if o.display_name == dupe["name_a"]), None)
            obj_b = next((o for o in objects if o.display_name == dupe["name_b"]), None)
            enriched.append({
                **dupe,
                "object_type": objects[0].object_type.value if objects else "unknown",
                "source_id_a": obj_a.source_id if obj_a else None,
                "source_id_b": obj_b.source_id if obj_b else None,
                "twin_id_a": str(obj_a.id) if obj_a and obj_a.id else None,
                "twin_id_b": str(obj_b.id) if obj_b and obj_b.id else None,
                "suggestion": f"Consider merging '{dupe['name_b']}' into '{dupe['name_a']}'",
            })
        return enriched

    def generate_suggestions(self, obj: TwinObjectBase) -> list[str]:
        """Human-readable normalization suggestions for an object."""
        suggestions: list[str] = []
        for issue in obj.issues:
            if issue.suggestion:
                suggestions.append(issue.suggestion)
            else:
                suggestions.append(f"Fix {issue.code}: {issue.message}")
        for note in obj.normalization_notes:
            suggestions.append(f"Auto-applied: {note}")
        if obj.quality_score < 70:
            suggestions.append("Overall data quality is low — review before using in reports")
        return suggestions

    def summarize_batch(self, objects: list[TwinObjectBase]) -> dict[str, Any]:
        if not objects:
            return {"count": 0, "avg_quality": 0, "issue_count": 0, "duplicates": []}
        avg_quality = sum(o.quality_score for o in objects) / len(objects)
        issue_count = sum(len(o.issues) for o in objects)
        duplicates = self.detect_duplicates(objects)
        return {
            "count": len(objects),
            "avg_quality": round(avg_quality, 2),
            "issue_count": issue_count,
            "duplicates": duplicates,
            "object_type": objects[0].object_type.value if objects else None,
        }
