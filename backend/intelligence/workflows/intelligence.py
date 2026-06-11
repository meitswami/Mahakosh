"""Workflow intelligence — performance, delays, agent efficiency, failures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.approval import ApprovalQueue
from backend.models.workflow import Workflow, WorkflowStep
from backend.models.workflow_monitoring import WorkflowMetric
class WorkflowIntelligence:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _monitor(self):
        from backend.workflows.execution_monitor import ExecutionMonitor
        return ExecutionMonitor(self.db)

    async def analyze(self, tenant_id: UUID, days: int = 30) -> dict[str, Any]:
        analytics = await self._monitor().get_analytics(tenant_id, days)
        since = datetime.now(UTC) - timedelta(days=days)

        type_breakdown = await self._type_breakdown(tenant_id, since)
        failure_analysis = await self._failure_analysis(tenant_id, since)
        approval_delays = await self._approval_delays(tenant_id)
        execution_trends = await self._execution_trends(tenant_id, days)

        return {
            "performance": {
                "completed": analytics["completed_workflows"],
                "failed": analytics["failed_workflows"],
                "success_rate_pct": analytics["success_rate"],
                "avg_duration_ms": analytics["average_duration_ms"],
                "active_agents": analytics["active_agents"],
            },
            "agent_efficiency": analytics["agent_utilization"],
            "type_breakdown": type_breakdown,
            "failure_analysis": failure_analysis,
            "approval_delays": approval_delays,
            "execution_trends": execution_trends,
        }

    async def _type_breakdown(self, tenant_id: UUID, since: datetime) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Workflow.workflow_type, Workflow.status, func.count())
            .where(Workflow.tenant_id == tenant_id, Workflow.created_at >= since)
            .group_by(Workflow.workflow_type, Workflow.status)
        )
        breakdown: dict[str, dict[str, int]] = {}
        for wf_type, status, count in result.fetchall():
            breakdown.setdefault(wf_type, {})[status] = count
        return [
            {"workflow_type": t, "counts": counts, "total": sum(counts.values())}
            for t, counts in breakdown.items()
        ]

    async def _failure_analysis(self, tenant_id: UUID, since: datetime) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Workflow)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.status == "failed",
                Workflow.created_at >= since,
            )
            .order_by(Workflow.created_at.desc())
            .limit(20)
        )
        failures = []
        for wf in result.scalars().all():
            step_result = await self.db.execute(
                select(WorkflowStep)
                .where(WorkflowStep.workflow_id == wf.id, WorkflowStep.status == "failed")
                .limit(1)
            )
            failed_step = step_result.scalar_one_or_none()
            failures.append({
                "workflow_id": str(wf.id),
                "name": wf.name,
                "workflow_type": wf.workflow_type,
                "failed_step": failed_step.step_name if failed_step else None,
                "error": failed_step.error_message if failed_step else wf.error_message,
                "created_at": wf.created_at.isoformat(),
            })
        return failures

    async def _approval_delays(self, tenant_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(ApprovalQueue).where(
                ApprovalQueue.tenant_id == tenant_id,
                ApprovalQueue.status == "pending",
            )
        )
        pending = list(result.scalars().all())
        now = datetime.now(UTC)
        delays = []
        for p in pending:
            age_hours = (now - p.created_at.replace(tzinfo=UTC)).total_seconds() / 3600
            delays.append({
                "id": str(p.id),
                "title": p.title,
                "priority": p.priority,
                "age_hours": round(age_hours, 1),
                "entity_type": p.entity_type,
            })
        avg_age = round(sum(d["age_hours"] for d in delays) / len(delays), 1) if delays else 0
        return {
            "pending_count": len(delays),
            "avg_pending_hours": avg_age,
            "items": sorted(delays, key=lambda x: x["age_hours"], reverse=True)[:10],
        }

    async def _execution_trends(self, tenant_id: UUID, days: int) -> list[dict[str, Any]]:
        since = datetime.now(UTC).date() - timedelta(days=days)
        result = await self.db.execute(
            select(WorkflowMetric)
            .where(
                WorkflowMetric.tenant_id == tenant_id,
                WorkflowMetric.metric_date >= since,
            )
            .order_by(WorkflowMetric.metric_date)
        )
        metrics = result.scalars().all()
        daily: dict[str, dict[str, int]] = {}
        for m in metrics:
            key = m.metric_date.strftime("%Y-%m-%d")
            daily.setdefault(key, {"completed": 0, "failed": 0})
            daily[key]["completed"] += m.completed_count
            daily[key]["failed"] += m.failed_count
        return [{"date": d, **counts} for d, counts in sorted(daily.items())]
