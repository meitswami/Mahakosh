"""Operational intelligence — documents, OCR, sync activity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.document import Document
from backend.models.accounting import SyncJob
from backend.models.ocr_job import OCRJob


class OperationalIntelligence:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(self, tenant_id: UUID, days: int = 30) -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=days)

        doc_count = (await self.db.execute(
            select(func.count()).select_from(Document).where(
                Document.tenant_id == tenant_id,
                Document.created_at >= since,
            )
        )).scalar() or 0

        ocr_count = (await self.db.execute(
            select(func.count()).select_from(OCRJob).where(
                OCRJob.tenant_id == tenant_id,
                OCRJob.created_at >= since,
            )
        )).scalar() or 0

        ocr_completed = (await self.db.execute(
            select(func.count()).select_from(OCRJob).where(
                OCRJob.tenant_id == tenant_id,
                OCRJob.status == "completed",
                OCRJob.created_at >= since,
            )
        )).scalar() or 0

        sync_jobs = (await self.db.execute(
            select(func.count()).select_from(SyncJob).where(
                SyncJob.tenant_id == tenant_id,
                SyncJob.created_at >= since,
            )
        )).scalar() or 0

        sync_completed = (await self.db.execute(
            select(func.count()).select_from(SyncJob).where(
                SyncJob.tenant_id == tenant_id,
                SyncJob.status == "completed",
                SyncJob.created_at >= since,
            )
        )).scalar() or 0

        return {
            "period_days": days,
            "documents_processed": doc_count,
            "ocr_jobs": ocr_count,
            "ocr_completed": ocr_completed,
            "ocr_success_rate_pct": round(ocr_completed / ocr_count * 100, 1) if ocr_count else 100.0,
            "sync_jobs": sync_jobs,
            "sync_completed": sync_completed,
            "sync_success_rate_pct": round(sync_completed / sync_jobs * 100, 1) if sync_jobs else 100.0,
        }
