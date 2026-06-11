from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.base.types import ImportEntityType, SyncMode
from backend.connectors.accounting.twin.service import TwinService
from backend.models.accounting import AccountingConnector, SyncJob, SyncLog

logger = structlog.get_logger(__name__)


class SyncEngine:
    """Orchestrates manual, scheduled, folder-watch, and workflow-triggered sync."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_sync(
        self,
        connector_record: AccountingConnector,
        sync_type: str = "ledgers",
        mode: SyncMode = SyncMode.MANUAL,
        options: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        opts = options or {}
        job = SyncJob(
            tenant_id=connector_record.tenant_id,
            connector_id=connector_record.id,
            name=f"{sync_type} sync — {mode.value}",
            sync_type=sync_type,
            trigger_mode=mode.value,
            status="running",
            config=opts,
            created_by=user_id or connector_record.created_by,
        )
        self.db.add(job)
        await self.db.flush()

        await self._log(job, "info", f"Starting {sync_type} sync via {connector_record.connector_type}")

        try:
            connector = accounting_connector_registry.create_instance(
                connector_record.connector_type,
                connector_record.config,
            )
            connect_result = await connector.connect()
            if not connect_result.success:
                job.status = "failed"
                await self._log(job, "error", connect_result.error or "Connection failed")
                await self.db.flush()
                return {"success": False, "job_id": str(job.id), "error": connect_result.error}

            entity_map = {
                "full": ImportEntityType.LEDGERS,
                "ledgers": ImportEntityType.LEDGERS,
                "items": ImportEntityType.STOCK_ITEMS,
                "vouchers": ImportEntityType.VOUCHERS,
                "outstanding": ImportEntityType.OUTSTANDING,
            }
            entity = entity_map.get(sync_type, ImportEntityType.LEDGERS)
            result = await connector.import_entities(
                entity,
                company_name=opts.get("company_name"),
                options=opts,
            )

            if result.success:
                count = result.data.get("count", 0)
                twin_service = TwinService(self.db)
                twin_result = await twin_service.process_import(
                    tenant_id=connector_record.tenant_id,
                    raw_data=result.data,
                    entity_type=entity,
                    source_system=connector_record.connector_type,
                    connector_id=connector_record.id,
                    sync_job_id=job.id,
                    user_id=user_id,
                )
                result.data["twin"] = twin_result
                job.status = "completed"
                job.last_run_at = datetime.now(timezone.utc)
                connector_record.last_sync_at = job.last_run_at
                connector_record.status = "connected"
                await self._log(job, "info", f"Sync completed — {count} records", result.data)
                if user_id:
                    await self._notify_sync_complete(
                        connector_record.tenant_id,
                        user_id,
                        sync_type,
                        count,
                        connector_record.name,
                    )
            else:
                job.status = "failed"
                await self._log(job, "error", result.error or "Sync failed")

            await connector.disconnect()
            await self.db.flush()

            return {
                "success": result.success,
                "job_id": str(job.id),
                "status": job.status,
                "data": result.data,
                "error": result.error,
                "warnings": result.warnings,
            }
        except Exception as exc:
            job.status = "failed"
            await self._log(job, "error", str(exc))
            await self.db.flush()
            logger.exception("sync_failed", job_id=str(job.id))
            return {"success": False, "job_id": str(job.id), "error": str(exc)}

    async def _notify_sync_complete(
        self,
        tenant_id: UUID,
        user_id: UUID,
        sync_type: str,
        record_count: int,
        connector_name: str,
    ) -> None:
        try:
            from backend.channels.base.types import NotificationEvent
            from backend.channels.notification_center import NotificationCenter

            center = NotificationCenter(self.db)
            await center.notify(
                tenant_id,
                user_id,
                NotificationEvent.SYNC_COMPLETE,
                {
                    "sync_type": sync_type,
                    "record_count": str(record_count),
                    "connector_name": connector_name,
                },
            )
        except Exception as exc:
            logger.warning("sync_notification_failed", error=str(exc))

    async def _log(self, job: SyncJob, level: str, message: str, details: dict | None = None) -> None:
        log = SyncLog(
            tenant_id=job.tenant_id,
            sync_job_id=job.id,
            level=level,
            message=message,
            details=details or {},
        )
        self.db.add(log)
