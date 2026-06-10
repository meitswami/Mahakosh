"""Temporal worker entry point for Mahakosh workflows."""

import asyncio

import structlog

from backend.core.config import settings

logger = structlog.get_logger(__name__)


async def run_worker() -> None:
    from temporalio.client import Client
    from temporalio.worker import Worker

    from backend.temporal.activities import execute_mahakosh_workflow, execute_workflow_step
    from backend.temporal.workflows import MahakoshWorkflow

    client = await Client.connect(settings.temporal_address)
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[MahakoshWorkflow],
        activities=[execute_mahakosh_workflow, execute_workflow_step],
    )
    logger.info("temporal_worker_started", task_queue=settings.TEMPORAL_TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
