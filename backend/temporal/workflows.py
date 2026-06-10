"""Temporal workflow definitions for Mahakosh."""

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from backend.temporal.activities import execute_mahakosh_workflow


@workflow.defn
class MahakoshWorkflow:
    """Durable wrapper around the in-process Mahakosh workflow engine."""

    def __init__(self) -> None:
        self._cancelled = False
        self._retry_from: str | None = None

    @workflow.signal
    async def cancel(self) -> None:
        self._cancelled = True

    @workflow.signal
    async def retry(self, from_step: str | None = None) -> None:
        self._retry_from = from_step

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._cancelled:
            return {"status": "cancelled"}

        return await workflow.execute_activity(
            execute_mahakosh_workflow,
            params,
            start_to_close_timeout=timedelta(hours=1),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
            ),
        )
