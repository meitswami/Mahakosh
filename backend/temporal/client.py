"""Temporal client for durable workflow execution."""

from uuid import UUID

import structlog

from backend.core.config import settings

logger = structlog.get_logger(__name__)


class TemporalClient:
    """Lazy Temporal client wrapper. Falls back gracefully when Temporal is unavailable."""

    def __init__(self) -> None:
        self._client = None

    async def connect(self):
        if self._client is not None:
            return self._client
        try:
            from temporalio.client import Client

            self._client = await Client.connect(settings.temporal_address)
            logger.info("temporal_connected", host=settings.temporal_address)
            return self._client
        except Exception as exc:
            logger.warning("temporal_unavailable", error=str(exc))
            return None

    async def start_workflow(
        self,
        workflow_type: str,
        workflow_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        input_data: dict,
    ) -> dict | None:
        client = await self.connect()
        if not client:
            return None

        from backend.temporal.workflows import MahakoshWorkflow

        handle = await client.start_workflow(
            MahakoshWorkflow.run,
            {
                "workflow_type": workflow_type,
                "workflow_id": str(workflow_id),
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "input_data": input_data,
            },
            id=f"mahakosh-{workflow_id}",
            task_queue=settings.TEMPORAL_TASK_QUEUE,
        )
        return {
            "temporal_workflow_id": handle.id,
            "temporal_run_id": handle.result_run_id,
        }

    async def signal_retry(self, workflow_id: UUID, from_step: str | None = None) -> bool:
        client = await self.connect()
        if not client:
            return False
        try:
            handle = client.get_workflow_handle(f"mahakosh-{workflow_id}")
            await handle.signal("retry", from_step)
            return True
        except Exception as exc:
            logger.error("temporal_signal_failed", error=str(exc))
            return False

    async def signal_cancel(self, workflow_id: UUID) -> bool:
        client = await self.connect()
        if not client:
            return False
        try:
            handle = client.get_workflow_handle(f"mahakosh-{workflow_id}")
            await handle.signal("cancel")
            return True
        except Exception as exc:
            logger.error("temporal_cancel_failed", error=str(exc))
            return False


temporal_client = TemporalClient()
