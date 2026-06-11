"""Usage tracking — documents, OCR, storage, agents, workflows, API."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.platform import UsageMetric
from backend.platform.plans import get_plan, plan_limit


class UsageTracker:
    METRIC_TYPES = (
        "documents_processed",
        "ocr_usage",
        "storage_bytes",
        "agent_executions",
        "workflow_runs",
        "api_calls",
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        tenant_id: UUID,
        metric_type: str,
        quantity: int = 1,
        metadata: dict | None = None,
    ) -> UsageMetric:
        today = date.today()
        existing = await self.db.execute(
            select(UsageMetric).where(
                UsageMetric.tenant_id == tenant_id,
                UsageMetric.metric_type == metric_type,
                UsageMetric.metric_date == today,
            )
        )
        metric = existing.scalar_one_or_none()
        if metric:
            metric.quantity += quantity
            if metadata:
                metric.metadata_ = {**metric.metadata_, **metadata}
        else:
            metric = UsageMetric(
                tenant_id=tenant_id,
                metric_type=metric_type,
                metric_date=today,
                quantity=quantity,
                metadata_=metadata or {},
            )
            self.db.add(metric)
        await self.db.flush()
        return metric

    async def get_usage_summary(self, tenant_id: UUID, days: int = 30) -> dict:
        since = date.today()
        from datetime import timedelta
        since = since - timedelta(days=days)

        result = await self.db.execute(
            select(
                UsageMetric.metric_type,
                func.sum(UsageMetric.quantity).label("total"),
            )
            .where(
                UsageMetric.tenant_id == tenant_id,
                UsageMetric.metric_date >= since,
            )
            .group_by(UsageMetric.metric_type)
        )
        usage = {row[0]: int(row[1]) for row in result.fetchall()}

        plan_tier = await self._get_plan_tier(tenant_id)
        plan = get_plan(plan_tier)
        limits = {
            "documents_processed": plan.get("max_documents_per_month", 0),
            "ocr_usage": plan.get("max_ocr_per_month", 0),
            "storage_bytes": plan.get("max_storage_gb", 0) * 1024 * 1024 * 1024,
            "agent_executions": plan.get("max_agent_executions_per_month", 0),
            "workflow_runs": plan.get("max_workflow_runs_per_month", 0),
            "api_calls": plan.get("max_api_calls_per_month", 0),
        }

        utilization = {}
        for metric_type, limit in limits.items():
            used = usage.get(metric_type, 0)
            utilization[metric_type] = {
                "used": used,
                "limit": limit,
                "pct": round(used / limit * 100, 1) if limit > 0 else 0,
            }

        return {
            "period_days": days,
            "plan_tier": plan_tier,
            "usage": usage,
            "limits": limits,
            "utilization": utilization,
        }

    async def check_limit(self, tenant_id: UUID, metric_type: str, quantity: int = 1) -> bool:
        summary = await self.get_usage_summary(tenant_id, days=30)
        util = summary["utilization"].get(metric_type, {})
        limit = util.get("limit", 0)
        used = util.get("used", 0)
        if limit <= 0:
            return True
        return (used + quantity) <= limit

    async def _get_plan_tier(self, tenant_id: UUID) -> str:
        from backend.models.platform import Subscription
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(["active", "trial"]),
            ).limit(1)
        )
        sub = result.scalar_one_or_none()
        if sub:
            return sub.plan_tier
        from backend.models.tenant import Tenant
        tenant = await self.db.get(Tenant, tenant_id)
        return tenant.subscription_tier if tenant else "starter"
