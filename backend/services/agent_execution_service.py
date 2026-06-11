from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base.types import AgentContext, AgentEventType, AgentResult
from backend.agents.communication.events import AgentEvent
from backend.agents.communication.event_bus import event_bus
from backend.agents.registry.registry import agent_registry
from backend.models.agent import AgentExecution
from backend.models.agent_swarm import AgentEventRecord, AgentHealthRecord

logger = structlog.get_logger(__name__)


class AgentExecutionService:
    """Persists agent executions, events, and health metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_agent(
        self,
        agent_name: str,
        input_data: dict[str, Any],
        tenant_id: UUID,
        user_id: UUID | None = None,
        workflow_id: UUID | None = None,
        parent_execution_id: UUID | None = None,
        model_name: str | None = None,
    ) -> tuple[AgentResult, AgentExecution]:
        agent = agent_registry.get_instance(agent_name, model_name)

        execution = AgentExecution(
            tenant_id=tenant_id,
            agent_name=agent_name,
            agent_version=agent.version,
            status="running",
            input_data=input_data,
            model_name=model_name or agent.model_name,
            triggered_by=user_id,
            workflow_id=workflow_id,
            parent_execution_id=parent_execution_id,
            started_at=datetime.now(UTC),
        )
        self.db.add(execution)
        await self.db.flush()

        context = AgentContext(
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_id=workflow_id,
            parent_execution_id=parent_execution_id,
            execution_id=execution.id,
            metadata={"db": self.db},
        )

        await self._record_event(
            tenant_id, agent_name, AgentEventType.AGENT_STARTED,
            {"execution_id": str(execution.id), "input_keys": list(input_data.keys())},
        )

        result = await agent.run(input_data, context)
        report = await agent.report(result, context)

        execution.status = "completed" if result.success else "failed"
        execution.output_data = result.to_output_dict()
        execution.error_message = result.error
        execution.confidence = result.confidence
        execution.reasoning = result.reasoning
        execution.sources = result.sources
        execution.reasoning_summary = report.get("reasoning_summary", "")
        execution.processing_time_ms = result.processing_time_ms
        execution.completed_at = datetime.now(UTC)
        execution.tokens_used = result.tokens_used

        await self._update_health(agent_name, tenant_id, result)
        await self._record_event(
            tenant_id, agent_name,
            AgentEventType.AGENT_COMPLETED if result.success else AgentEventType.AGENT_FAILED,
            {"execution_id": str(execution.id), "confidence": result.confidence},
        )

        await self._track_execution(tenant_id)
        await self.db.flush()
        return result, execution

    async def _track_execution(self, tenant_id: UUID) -> None:
        from backend.platform.usage_tracker import UsageTracker
        await UsageTracker(self.db).record(tenant_id, "agent_executions")

    async def _record_event(
        self,
        tenant_id: UUID,
        source_agent: str,
        event_type: AgentEventType,
        payload: dict[str, Any],
    ) -> None:
        record = AgentEventRecord(
            tenant_id=tenant_id,
            event_type=event_type.value,
            source_agent=source_agent,
            payload=payload,
        )
        self.db.add(record)
        await event_bus.publish(AgentEvent(
            event_type=event_type,
            tenant_id=tenant_id,
            source_agent=source_agent,
            payload=payload,
        ))

    async def _update_health(self, agent_name: str, tenant_id: UUID, result: AgentResult) -> None:
        existing = await self.db.execute(
            select(AgentHealthRecord).where(
                AgentHealthRecord.tenant_id == tenant_id,
                AgentHealthRecord.agent_name == agent_name,
            )
        )
        health = existing.scalar_one_or_none()
        if not health:
            health = AgentHealthRecord(
                tenant_id=tenant_id,
                agent_name=agent_name,
                status="idle",
            )
            self.db.add(health)

        health.execution_count += 1
        if result.success:
            health.success_count += 1
        else:
            health.error_count += 1
            health.last_error = result.error
        health.total_runtime_ms += result.processing_time_ms or 0
        health.average_runtime_ms = health.total_runtime_ms / health.execution_count
        health.success_rate = round((health.success_count / health.execution_count) * 100, 2)
        health.status = "healthy" if health.success_rate >= 50 else "degraded"
        health.last_checked_at = datetime.now(UTC)

    async def list_executions(
        self,
        tenant_id: UUID,
        agent_name: str | None = None,
        limit: int = 50,
    ) -> list[AgentExecution]:
        q = select(AgentExecution).where(AgentExecution.tenant_id == tenant_id)
        if agent_name:
            q = q.where(AgentExecution.agent_name == agent_name)
        q = q.order_by(AgentExecution.created_at.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def list_events(self, tenant_id: UUID, limit: int = 50) -> list[AgentEventRecord]:
        result = await self.db.execute(
            select(AgentEventRecord)
            .where(AgentEventRecord.tenant_id == tenant_id)
            .order_by(AgentEventRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_health(self, tenant_id: UUID) -> list[AgentHealthRecord]:
        result = await self.db.execute(
            select(AgentHealthRecord).where(AgentHealthRecord.tenant_id == tenant_id)
        )
        return list(result.scalars().all())
