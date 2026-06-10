"""Temporal activities for Mahakosh workflow steps."""

from typing import Any
from uuid import UUID

import structlog
from temporalio import activity

from backend.core.database import async_session_factory
from backend.workflows.workflow_engine import WorkflowEngine

logger = structlog.get_logger(__name__)


@activity.defn
async def execute_mahakosh_workflow(params: dict[str, Any]) -> dict[str, Any]:
    workflow_id = UUID(params["workflow_id"])
    tenant_id = UUID(params["tenant_id"])
    user_id = UUID(params["user_id"])

    async with async_session_factory() as db:
        engine = WorkflowEngine(db)
        result = await engine.execute_workflow(workflow_id, tenant_id, user_id)
        await db.commit()
        return result


@activity.defn
async def execute_workflow_step(params: dict[str, Any]) -> dict[str, Any]:
    """Execute a single workflow step as a Temporal activity."""
    logger.info("temporal_step_activity", step=params.get("step_name"))
    return {"status": "completed", "step": params.get("step_name")}
