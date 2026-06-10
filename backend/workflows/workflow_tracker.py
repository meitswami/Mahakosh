import json
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.workflow_monitoring import WorkflowEventRecord, WorkflowLog
from backend.workflows.workflow_events import WorkflowEvent, WorkflowEventType

logger = structlog.get_logger(__name__)

LIVE_CHANNEL = "mahakosh:workflows:live"


class WorkflowTracker:
    """Track workflow execution, emit events, persist logs."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._redis = None

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(str(settings.REDIS_URL), decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception:
            return None

    async def emit(self, event: WorkflowEvent) -> WorkflowEventRecord:
        record = WorkflowEventRecord(
            tenant_id=event.tenant_id,
            workflow_id=event.workflow_id,
            event_type=event.event_type.value,
            agent_name=event.agent_name,
            user_id=event.user_id,
            payload=event.payload,
        )
        self.db.add(record)
        await self.db.flush()

        redis = await self._get_redis()
        if redis:
            channel = f"{LIVE_CHANNEL}:{event.tenant_id}"
            await redis.publish(channel, json.dumps(event.to_dict()))

        logger.info(
            "workflow_event",
            event_type=event.event_type.value,
            workflow_id=str(event.workflow_id),
        )
        return record

    async def log_execution(
        self,
        tenant_id: UUID,
        workflow_id: UUID,
        action: str,
        *,
        step_id: UUID | None = None,
        agent_name: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        reasoning_summary: str | None = None,
        confidence: float | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
        user_id: UUID | None = None,
    ) -> WorkflowLog:
        log = WorkflowLog(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            step_id=step_id,
            agent_name=agent_name,
            action=action,
            input_data=input_data or {},
            output_data=output_data or {},
            reasoning_summary=reasoning_summary,
            confidence=confidence,
            duration_ms=duration_ms,
            error_message=error_message,
            user_id=user_id,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def event(
        self,
        event_type: WorkflowEventType,
        workflow_id: UUID,
        tenant_id: UUID,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> WorkflowEventRecord:
        return await self.emit(WorkflowEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            payload=payload or {},
            **kwargs,
        ))
