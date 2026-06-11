"""Twin repository — persistence for normalized accounting objects."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.twin.objects import TwinObjectBase, TwinObjectType
from backend.models.accounting_twin import (
    AccountingAlias,
    AccountingDataIssue,
    AccountingNormalizationJob,
    AccountingTwinObject,
)


class TwinRepository:
    """Persist and query digital twin objects per tenant."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_aliases(self, tenant_id: UUID, entity_type: str | None = None) -> dict[str, str]:
        query = select(AccountingAlias).where(AccountingAlias.tenant_id == tenant_id)
        if entity_type:
            query = query.where(AccountingAlias.entity_type == entity_type)
        result = await self.db.execute(query)
        return {a.alias_name.lower(): a.canonical_name for a in result.scalars().all()}

    async def upsert_objects(
        self,
        tenant_id: UUID,
        objects: list[TwinObjectBase],
    ) -> list[AccountingTwinObject]:
        """Upsert twin objects by tenant + source_system + source_id + object_type."""
        persisted: list[AccountingTwinObject] = []
        for obj in objects:
            existing = await self.db.execute(
                select(AccountingTwinObject).where(
                    AccountingTwinObject.tenant_id == tenant_id,
                    AccountingTwinObject.source_system == obj.source_system,
                    AccountingTwinObject.source_id == obj.source_id,
                    AccountingTwinObject.object_type == obj.object_type.value,
                )
            )
            record = existing.scalar_one_or_none()
            if record:
                record.display_name = obj.display_name
                record.raw_payload = obj.raw_payload
                record.normalized_fields = obj.normalized_fields
                record.quality_score = obj.quality_score
                record.issues = [i.to_dict() for i in obj.issues]
                record.normalization_notes = obj.normalization_notes
                record.connector_id = obj.connector_id
                record.sync_job_id = obj.sync_job_id
            else:
                record = AccountingTwinObject(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    connector_id=obj.connector_id,
                    sync_job_id=obj.sync_job_id,
                    object_type=obj.object_type.value,
                    source_system=obj.source_system,
                    source_id=obj.source_id,
                    display_name=obj.display_name,
                    raw_payload=obj.raw_payload,
                    normalized_fields=obj.normalized_fields,
                    quality_score=obj.quality_score,
                    issues=[i.to_dict() for i in obj.issues],
                    normalization_notes=obj.normalization_notes,
                )
                self.db.add(record)
            obj.id = record.id
            persisted.append(record)

            for issue in obj.issues:
                await self._upsert_issue(tenant_id, record.id, issue.to_dict())

        await self.db.flush()
        return persisted

    async def _upsert_issue(self, tenant_id: UUID, twin_object_id: UUID, issue: dict[str, Any]) -> None:
        existing = await self.db.execute(
            select(AccountingDataIssue).where(
                AccountingDataIssue.tenant_id == tenant_id,
                AccountingDataIssue.twin_object_id == twin_object_id,
                AccountingDataIssue.code == issue["code"],
                AccountingDataIssue.status == "open",
            )
        )
        record = existing.scalar_one_or_none()
        if record:
            record.message = issue["message"]
            record.severity = issue["severity"]
            record.suggestion = issue.get("suggestion")
        else:
            self.db.add(AccountingDataIssue(
                id=uuid4(),
                tenant_id=tenant_id,
                twin_object_id=twin_object_id,
                issue_type=issue.get("field") or issue["code"],
                code=issue["code"],
                severity=issue["severity"],
                message=issue["message"],
                suggestion=issue.get("suggestion"),
                status="open",
            ))

    async def create_normalization_job(
        self,
        tenant_id: UUID,
        connector_id: UUID | None,
        created_by: UUID,
        entity_types: list[str],
        sync_job_id: UUID | None = None,
    ) -> AccountingNormalizationJob:
        job = AccountingNormalizationJob(
            id=uuid4(),
            tenant_id=tenant_id,
            connector_id=connector_id,
            sync_job_id=sync_job_id,
            status="running",
            entity_types=entity_types,
            started_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def complete_normalization_job(
        self,
        job_id: UUID,
        stats: dict[str, Any],
        error: str | None = None,
    ) -> None:
        status = "failed" if error else "completed"
        await self.db.execute(
            update(AccountingNormalizationJob)
            .where(AccountingNormalizationJob.id == job_id)
            .values(
                status=status,
                stats=stats,
                completed_at=datetime.now(timezone.utc),
                error_message=error,
            )
        )

    async def list_objects(
        self,
        tenant_id: UUID,
        object_type: str,
        page: int = 1,
        page_size: int = 20,
        min_quality: float | None = None,
        connector_id: UUID | None = None,
    ) -> tuple[list[AccountingTwinObject], int]:
        query = select(AccountingTwinObject).where(
            AccountingTwinObject.tenant_id == tenant_id,
            AccountingTwinObject.object_type == object_type,
            AccountingTwinObject.is_merged.is_(False),
        )
        if min_quality is not None:
            query = query.where(AccountingTwinObject.quality_score >= min_quality)
        if connector_id:
            query = query.where(AccountingTwinObject.connector_id == connector_id)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        result = await self.db.execute(
            query.order_by(AccountingTwinObject.display_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def list_issues(
        self,
        tenant_id: UUID,
        status: str = "open",
        severity: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AccountingDataIssue], int]:
        query = select(AccountingDataIssue).where(
            AccountingDataIssue.tenant_id == tenant_id,
            AccountingDataIssue.status == status,
        )
        if severity:
            query = query.where(AccountingDataIssue.severity == severity)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        result = await self.db.execute(
            query.order_by(AccountingDataIssue.severity.desc(), AccountingDataIssue.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def resolve_issue(
        self,
        tenant_id: UUID,
        issue_id: UUID,
        user_id: UUID,
        resolution: str,
        status: str = "resolved",
    ) -> AccountingDataIssue | None:
        result = await self.db.execute(
            select(AccountingDataIssue).where(
                AccountingDataIssue.id == issue_id,
                AccountingDataIssue.tenant_id == tenant_id,
            )
        )
        issue = result.scalar_one_or_none()
        if not issue:
            return None
        issue.status = status
        issue.resolved_by = user_id
        issue.resolved_at = datetime.now(timezone.utc)
        issue.resolution_notes = resolution
        await self.db.flush()
        return issue

    async def merge_duplicates(
        self,
        tenant_id: UUID,
        source_id: UUID,
        target_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        source_result = await self.db.execute(
            select(AccountingTwinObject).where(
                AccountingTwinObject.id == source_id,
                AccountingTwinObject.tenant_id == tenant_id,
            )
        )
        source = source_result.scalar_one_or_none()
        target_result = await self.db.execute(
            select(AccountingTwinObject).where(
                AccountingTwinObject.id == target_id,
                AccountingTwinObject.tenant_id == tenant_id,
            )
        )
        target = target_result.scalar_one_or_none()
        if not source or not target:
            return {"success": False, "error": "Source or target object not found"}
        if source.object_type != target.object_type:
            return {"success": False, "error": "Cannot merge objects of different types"}

        source.is_merged = True
        source.merged_into_id = target.id
        source.normalization_notes = list(source.normalization_notes or []) + [
            f"Merged into '{target.display_name}' by user"
        ]

        alias_name = source.display_name.lower().strip()
        existing_alias = await self.db.execute(
            select(AccountingAlias).where(
                AccountingAlias.tenant_id == tenant_id,
                AccountingAlias.alias_name == alias_name,
            )
        )
        if not existing_alias.scalar_one_or_none():
            self.db.add(AccountingAlias(
                id=uuid4(),
                tenant_id=tenant_id,
                entity_type=source.object_type,
                canonical_name=target.display_name,
                alias_name=alias_name,
                source="user_merge",
                twin_object_id=target.id,
                created_by=user_id,
            ))

        await self.db.flush()
        return {
            "success": True,
            "merged": source.display_name,
            "into": target.display_name,
            "target_id": str(target.id),
        }

    async def get_overview(self, tenant_id: UUID) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for obj_type in TwinObjectType:
            count = (await self.db.execute(
                select(func.count()).where(
                    AccountingTwinObject.tenant_id == tenant_id,
                    AccountingTwinObject.object_type == obj_type.value,
                    AccountingTwinObject.is_merged.is_(False),
                )
            )).scalar() or 0
            if count:
                type_counts[obj_type.value] = count

        avg_quality = (await self.db.execute(
            select(func.avg(AccountingTwinObject.quality_score)).where(
                AccountingTwinObject.tenant_id == tenant_id,
                AccountingTwinObject.is_merged.is_(False),
            )
        )).scalar()

        open_issues = (await self.db.execute(
            select(func.count()).where(
                AccountingDataIssue.tenant_id == tenant_id,
                AccountingDataIssue.status == "open",
            )
        )).scalar() or 0

        error_issues = (await self.db.execute(
            select(func.count()).where(
                AccountingDataIssue.tenant_id == tenant_id,
                AccountingDataIssue.status == "open",
                AccountingDataIssue.severity == "error",
            )
        )).scalar() or 0

        return {
            "object_counts": type_counts,
            "total_objects": sum(type_counts.values()),
            "avg_quality_score": round(float(avg_quality or 0), 2),
            "open_issues": open_issues,
            "error_issues": error_issues,
        }

    async def get_twin_dicts(self, tenant_id: UUID, object_type: str) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(AccountingTwinObject).where(
                AccountingTwinObject.tenant_id == tenant_id,
                AccountingTwinObject.object_type == object_type,
                AccountingTwinObject.is_merged.is_(False),
            )
        )
        return [
            {
                "id": str(o.id),
                "name": o.display_name,
                **o.normalized_fields,
                "quality_score": float(o.quality_score),
                "source_system": o.source_system,
                "issues": o.issues,
            }
            for o in result.scalars().all()
        ]
