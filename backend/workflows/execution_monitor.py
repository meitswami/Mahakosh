from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.agent_swarm import AgentHealthRecord
from backend.models.workflow import Workflow, WorkflowStep
from backend.models.workflow_monitoring import WorkflowMetric


class ExecutionMonitor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_live_workflows(self, tenant_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(Workflow)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.status.in_(["queued", "running", "waiting", "paused"]),
            )
            .order_by(Workflow.started_at.desc().nullslast())
            .limit(50)
        )
        workflows = result.scalars().all()
        live = []
        for wf in workflows:
            steps_result = await self.db.execute(
                select(WorkflowStep)
                .where(WorkflowStep.workflow_id == wf.id)
                .order_by(WorkflowStep.step_order)
            )
            steps = list(steps_result.scalars().all())
            current = next((s for s in steps if s.status in ("running", "waiting")), None)
            completed = sum(1 for s in steps if s.status == "completed")
            live.append({
                "id": str(wf.id),
                "name": wf.name,
                "workflow_type": wf.workflow_type,
                "status": wf.status,
                "progress": round(completed / len(steps) * 100) if steps else 0,
                "current_step": current.step_name if current else None,
                "current_agent": current.agent_name if current else None,
                "started_at": wf.started_at.isoformat() if wf.started_at else None,
                "assigned_agents": wf.assigned_agents,
            })
        return live

    async def get_agent_activity(self, tenant_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(AgentHealthRecord).where(AgentHealthRecord.tenant_id == tenant_id)
        )
        agents = result.scalars().all()
        if not agents:
            return []
        return [
            {
                "agent_name": a.agent_name,
                "status": a.status,
                "healthy": a.success_rate >= 50,
                "queue_length": a.queue_length,
                "execution_count": a.execution_count,
                "average_runtime_ms": a.average_runtime_ms,
                "success_rate": a.success_rate,
                "last_error": a.last_error,
            }
            for a in agents
        ]

    async def get_analytics(self, tenant_id: UUID, days: int = 30) -> dict:
        since = datetime.now(UTC) - timedelta(days=days)
        completed = await self.db.execute(
            select(func.count()).select_from(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.status == "completed",
                Workflow.created_at >= since,
            )
        )
        failed = await self.db.execute(
            select(func.count()).select_from(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.status == "failed",
                Workflow.created_at >= since,
            )
        )
        total_completed = completed.scalar() or 0
        total_failed = failed.scalar() or 0

        durations = await self.db.execute(
            select(Workflow.started_at, Workflow.completed_at)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.status == "completed",
                Workflow.started_at.isnot(None),
                Workflow.completed_at.isnot(None),
                Workflow.created_at >= since,
            )
        )
        durs = [
            int((row[1] - row[0]).total_seconds() * 1000)
            for row in durations.fetchall()
            if row[0] and row[1]
        ]
        avg_duration = sum(durs) / len(durs) if durs else 0

        agent_activity = await self.get_agent_activity(tenant_id)
        agent_util = {
            a["agent_name"]: a["execution_count"]
            for a in agent_activity
        }

        return {
            "period_days": days,
            "completed_workflows": total_completed,
            "failed_workflows": total_failed,
            "success_rate": round(
                total_completed / (total_completed + total_failed) * 100, 1
            ) if (total_completed + total_failed) else 100.0,
            "average_duration_ms": round(avg_duration, 0),
            "agent_utilization": agent_util,
            "active_agents": len([a for a in agent_activity if a["status"] != "idle"]),
        }

    async def update_metrics(self, tenant_id: UUID, workflow: Workflow) -> None:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(WorkflowMetric).where(
                WorkflowMetric.tenant_id == tenant_id,
                WorkflowMetric.workflow_type == workflow.workflow_type,
                WorkflowMetric.metric_date == today,
            )
        )
        metric = result.scalar_one_or_none()
        if not metric:
            metric = WorkflowMetric(
                tenant_id=tenant_id,
                metric_date=today,
                workflow_type=workflow.workflow_type,
            )
            self.db.add(metric)

        if workflow.status == "completed":
            metric.completed_count += 1
        elif workflow.status == "failed":
            metric.failed_count += 1
        elif workflow.status == "cancelled":
            metric.cancelled_count += 1

        if workflow.started_at and workflow.completed_at:
            dur = int((workflow.completed_at - workflow.started_at).total_seconds() * 1000)
            total = metric.completed_count + metric.failed_count
            metric.avg_duration_ms = (
                (metric.avg_duration_ms * (total - 1) + dur) / total if total else dur
            )
