"""Twin service — orchestrates normalization, persistence, and knowledge ingestion."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.base.types import ImportEntityType
from backend.connectors.accounting.twin.normalizer import AccountingNormalizer
from backend.connectors.accounting.twin.repository import TwinRepository
from backend.connectors.accounting.twin_knowledge_bridge import ingest_twin_knowledge
from backend.models.audit import AuditLog
from backend.models.accounting_twin import AccountingTwinObject


class TwinService:
    """High-level digital twin operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TwinRepository(db)

    async def process_import(
        self,
        tenant_id: UUID,
        raw_data: dict[str, Any],
        entity_type: ImportEntityType,
        source_system: str,
        connector_id: UUID | None = None,
        sync_job_id: UUID | None = None,
        user_id: UUID | None = None,
        ingest_knowledge: bool = True,
    ) -> dict[str, Any]:
        """Raw connector data → normalize → persist → optional knowledge ingestion."""
        aliases = await self.repo.load_aliases(tenant_id)
        normalizer = AccountingNormalizer(aliases=aliases)
        objects = normalizer.normalize_import(
            entity_type, raw_data, source_system, connector_id, sync_job_id
        )
        if not objects:
            return {"normalized": 0, "avg_quality": 0, "issues": 0}

        persisted = await self.repo.upsert_objects(tenant_id, objects)
        summary = normalizer.summarize_batch(objects)

        if ingest_knowledge and user_id:
            knowledge_objects = [
                obj.to_dict() for obj in objects
            ]
            await ingest_twin_knowledge(None, tenant_id, user_id, knowledge_objects)

        if user_id:
            self.db.add(AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action="twin_import",
                entity_type=entity_type.value,
                description=f"Normalized {len(objects)} {entity_type.value} objects (avg quality {summary['avg_quality']})",
                new_values=summary,
            ))

        return {
            "normalized": len(persisted),
            "avg_quality": summary["avg_quality"],
            "issues": summary["issue_count"],
            "duplicates": summary["duplicates"],
        }

    async def run_normalization_job(
        self,
        tenant_id: UUID,
        connector_id: UUID | None,
        entity_types: list[str],
        user_id: UUID,
    ) -> dict[str, Any]:
        """Re-normalize existing twin objects for given entity types."""
        job = await self.repo.create_normalization_job(
            tenant_id, connector_id, user_id, entity_types
        )
        aliases = await self.repo.load_aliases(tenant_id)
        normalizer = AccountingNormalizer(aliases=aliases)
        total_stats: dict[str, Any] = {"entity_types": {}, "total_normalized": 0}

        try:
            for entity_type in entity_types:
                objects_raw = await self.repo.get_twin_dicts(tenant_id, entity_type)
                if not objects_raw:
                    continue
                raw_payload = self._rebuild_raw_payload(entity_type, objects_raw)
                import_type = self._entity_type_to_import(entity_type)
                if not import_type:
                    continue
                objects = normalizer.normalize_import(
                    import_type, raw_payload, "re_normalize", connector_id, job.id
                )
                await self.repo.upsert_objects(tenant_id, objects)
                batch_summary = normalizer.summarize_batch(objects)
                total_stats["entity_types"][entity_type] = batch_summary
                total_stats["total_normalized"] += len(objects)

            await self.repo.complete_normalization_job(job.id, total_stats)
            self.db.add(AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action="twin_normalize",
                entity_type="normalization_job",
                entity_id=job.id,
                description=f"Re-normalized {total_stats['total_normalized']} objects",
                new_values=total_stats,
            ))
            return {"job_id": str(job.id), "status": "completed", **total_stats}
        except Exception as exc:
            await self.repo.complete_normalization_job(job.id, total_stats, str(exc))
            raise

    async def get_overview(self, tenant_id: UUID) -> dict[str, Any]:
        return await self.repo.get_overview(tenant_id)

    async def list_objects(
        self,
        tenant_id: UUID,
        object_type: str,
        page: int = 1,
        page_size: int = 20,
        connector_id: UUID | None = None,
    ) -> tuple[list[AccountingTwinObject], int]:
        return await self.repo.list_objects(tenant_id, object_type, page, page_size, connector_id=connector_id)

    async def list_issues(
        self,
        tenant_id: UUID,
        status: str = "open",
        severity: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        return await self.repo.list_issues(tenant_id, status, severity, page, page_size)

    async def resolve_issue(
        self,
        tenant_id: UUID,
        issue_id: UUID,
        user_id: UUID,
        resolution: str,
    ) -> dict[str, Any]:
        issue = await self.repo.resolve_issue(tenant_id, issue_id, user_id, resolution)
        if not issue:
            return {"success": False, "error": "Issue not found"}
        self.db.add(AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="twin_resolve_issue",
            entity_type="data_issue",
            entity_id=issue.id,
            description=f"Resolved issue: {issue.code}",
            new_values={"resolution": resolution},
        ))
        return {"success": True, "issue_id": str(issue.id), "status": issue.status}

    async def merge_duplicate(
        self,
        tenant_id: UUID,
        source_id: UUID,
        target_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        result = await self.repo.merge_duplicates(tenant_id, source_id, target_id, user_id)
        if result.get("success"):
            self.db.add(AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action="twin_merge_duplicate",
                entity_type="twin_object",
                entity_id=target_id,
                description=f"Merged '{result['merged']}' into '{result['into']}'",
                new_values=result,
            ))
        return result

    @staticmethod
    def _entity_type_to_import(entity_type: str) -> ImportEntityType | None:
        mapping = {
            "ledger": ImportEntityType.LEDGERS,
            "stock_item": ImportEntityType.STOCK_ITEMS,
            "party": ImportEntityType.VENDORS,
            "voucher": ImportEntityType.VOUCHERS,
            "outstanding": ImportEntityType.OUTSTANDING,
            "ledger_group": ImportEntityType.GROUPS,
            "unit": ImportEntityType.UNITS,
        }
        return mapping.get(entity_type)

    @staticmethod
    def _rebuild_raw_payload(entity_type: str, objects: list[dict[str, Any]]) -> dict[str, Any]:
        if entity_type == "ledger":
            return {"ledgers": [{**o, "name": o.get("name", o.get("display_name"))} for o in objects]}
        if entity_type == "stock_item":
            return {"items": [{**o, "name": o.get("name", o.get("display_name"))} for o in objects]}
        if entity_type == "party":
            return {"ledgers": [{**o, "name": o.get("name", o.get("display_name"))} for o in objects]}
        if entity_type == "voucher":
            return {"vouchers": objects}
        if entity_type == "outstanding":
            return {"outstanding": objects}
        return {}
