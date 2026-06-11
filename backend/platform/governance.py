"""Enterprise governance — retention, audit policies, compliance center."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.approval import ApprovalQueue
from backend.models.audit import AuditLog
from backend.models.platform import GovernancePolicy, SecurityEvent
from backend.models.platform import TenantSetting


class GovernanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_compliance_center(self, tenant_id: UUID) -> dict:
        policies = await self._get_policies(tenant_id)
        audit_status = await self._audit_status(tenant_id)
        security_events = await self._recent_security_events(tenant_id)
        approval_history = await self._approval_summary(tenant_id)
        retention = await self._retention_status(tenant_id)

        return {
            "audit_status": audit_status,
            "retention_policies": retention,
            "governance_policies": policies,
            "security_events": security_events,
            "approval_history": approval_history,
            "data_governance": {
                "data_ownership": "tenant",
                "retention_days": retention.get("retention_days", 2555),
                "archival_enabled": retention.get("archival_enabled", False),
                "deletion_requests": retention.get("pending_deletions", 0),
                "audit_trail_complete": audit_status.get("complete", True),
            },
        }

    async def _get_policies(self, tenant_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(GovernancePolicy).where(
                GovernancePolicy.tenant_id == tenant_id,
                GovernancePolicy.is_active.is_(True),
            )
        )
        return [
            {
                "id": str(p.id),
                "policy_type": p.policy_type,
                "name": p.name,
                "description": p.description,
                "config": p.config,
            }
            for p in result.scalars().all()
        ]

    async def _audit_status(self, tenant_id: UUID) -> dict:
        since = datetime.now(UTC) - timedelta(days=30)
        count = (await self.db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at >= since,
            )
        )).scalar() or 0

        setting = await self._get_setting(tenant_id, "audit_enabled")
        return {
            "enabled": setting != "false",
            "events_last_30_days": count,
            "complete": count > 0 or setting == "false",
            "last_event_at": None,
        }

    async def _recent_security_events(self, tenant_id: UUID, limit: int = 20) -> list[dict]:
        result = await self.db.execute(
            select(SecurityEvent)
            .where(SecurityEvent.tenant_id == tenant_id)
            .order_by(SecurityEvent.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "description": e.description,
                "user_id": str(e.user_id) if e.user_id else None,
                "created_at": e.created_at.isoformat(),
            }
            for e in result.scalars().all()
        ]

    async def _approval_summary(self, tenant_id: UUID) -> dict:
        pending = (await self.db.execute(
            select(func.count()).select_from(ApprovalQueue).where(
                ApprovalQueue.tenant_id == tenant_id,
                ApprovalQueue.status == "pending",
            )
        )).scalar() or 0

        resolved = (await self.db.execute(
            select(func.count()).select_from(ApprovalQueue).where(
                ApprovalQueue.tenant_id == tenant_id,
                ApprovalQueue.status.in_(["approved", "rejected"]),
            )
        )).scalar() or 0

        return {"pending": pending, "resolved": resolved, "total": pending + resolved}

    async def _retention_status(self, tenant_id: UUID) -> dict:
        days = await self._get_setting(tenant_id, "retention_days")
        return {
            "retention_days": int(days) if days else 2555,
            "archival_enabled": await self._get_setting(tenant_id, "archival_enabled") == "true",
            "pending_deletions": 0,
        }

    async def _get_setting(self, tenant_id: UUID, key: str) -> str | None:
        result = await self.db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.setting_key == key,
            )
        )
        setting = result.scalar_one_or_none()
        return setting.setting_value if setting else None

    async def seed_default_policies(self, tenant_id: UUID) -> None:
        defaults = [
            ("retention", "Data Retention Policy", "Retain business data for 7 years per Indian regulations", {"days": 2555}),
            ("audit", "Audit Logging Policy", "Log all sensitive operations", {"enabled": True}),
            ("approval", "Approval Chain Policy", "Require approval for voucher creation and Tally writes", {"actions": ["voucher_create", "tally_write"]}),
        ]
        for policy_type, name, description, config in defaults:
            existing = await self.db.execute(
                select(GovernancePolicy).where(
                    GovernancePolicy.tenant_id == tenant_id,
                    GovernancePolicy.policy_type == policy_type,
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(GovernancePolicy(
                    tenant_id=tenant_id,
                    policy_type=policy_type,
                    name=name,
                    description=description,
                    config=config,
                ))
        await self.db.flush()

    async def log_security_event(
        self,
        tenant_id: UUID,
        event_type: str,
        description: str,
        severity: str = "info",
        user_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            severity=severity,
            description=description,
            user_id=user_id,
            metadata_=metadata or {},
        )
        self.db.add(event)
        await self.db.flush()
        return event
