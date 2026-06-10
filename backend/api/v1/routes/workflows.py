import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole, decode_token
from backend.models.workflow import Workflow, WorkflowStep
from backend.models.workflow_monitoring import WorkflowEventRecord, WorkflowLog
from backend.schemas.common import PaginatedResponse
from backend.schemas.workflows import (
    AgentActivityResponse,
    ApprovalItemResponse,
    LiveWorkflowResponse,
    TimelineEntry,
    WorkflowAnalyticsResponse,
    WorkflowCancelRequest,
    WorkflowCreateRequest,
    WorkflowDetailResponse,
    WorkflowGraphResponse,
    WorkflowLogResponse,
    WorkflowRetryRequest,
    WorkflowStepResponse,
    WorkflowSummaryResponse,
    WorkflowTemplateResponse,
    WorkflowTransparencyResponse,
)
from backend.workflows.approval_manager import ApprovalManager
from backend.workflows.execution_monitor import ExecutionMonitor
from backend.workflows.states import WorkflowState
from backend.workflows.timeline_builder import TimelineBuilder
from backend.workflows.transparency_builder import WorkflowTransparencyService
from backend.workflows.workflow_engine import WorkflowEngine
from backend.workflows.workflow_registry import workflow_registry
from backend.workflows.workflow_tracker import LIVE_CHANNEL
from backend.workflows.workflow_visualizer import WorkflowVisualizer

router = APIRouter()


def _get_engine(db: AsyncSession) -> WorkflowEngine:
    return WorkflowEngine(db)


async def _load_workflow_detail(
    db: AsyncSession,
    workflow_id: UUID,
    tenant_id: UUID,
) -> WorkflowDetailResponse:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps_result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.step_order)
    )
    steps = list(steps_result.scalars().all())

    duration_ms = None
    if workflow.started_at and workflow.completed_at:
        duration_ms = int((workflow.completed_at - workflow.started_at).total_seconds() * 1000)

    transparency_svc = WorkflowTransparencyService(db)
    try:
        manifest = await transparency_svc.build_for_workflow(workflow_id, tenant_id)
        transparency = WorkflowTransparencyResponse(**manifest)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowDetailResponse(
        id=workflow.id,
        name=workflow.name,
        workflow_type=workflow.workflow_type,
        status=workflow.status,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        assigned_agents=workflow.assigned_agents or [],
        created_at=workflow.created_at,
        input_data=workflow.input_data,
        output_data=workflow.output_data,
        error_message=workflow.error_message,
        duration_ms=duration_ms,
        steps=[WorkflowStepResponse.model_validate(s) for s in steps],
        created_by=workflow.created_by,
        transparency=transparency,
    )


@router.get("/templates", response_model=list[WorkflowTemplateResponse])
async def list_templates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[WorkflowTemplateResponse]:
    from backend.workflows.definitions import register_all_workflows

    register_all_workflows()
    return [WorkflowTemplateResponse(**t) for t in workflow_registry.list_templates()]


@router.get("", response_model=PaginatedResponse[WorkflowSummaryResponse])
async def list_workflows(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: WorkflowState | None = Query(None, alias="status"),
    workflow_type: str | None = None,
) -> PaginatedResponse[WorkflowSummaryResponse]:
    from sqlalchemy import func

    query = select(Workflow).where(Workflow.tenant_id == current_user.tenant_id)
    count_query = select(func.count()).select_from(Workflow).where(
        Workflow.tenant_id == current_user.tenant_id
    )
    if status_filter:
        query = query.where(Workflow.status == status_filter.value)
        count_query = count_query.where(Workflow.status == status_filter.value)
    if workflow_type:
        query = query.where(Workflow.workflow_type == workflow_type)
        count_query = count_query.where(Workflow.workflow_type == workflow_type)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Workflow.created_at.desc()).offset(offset).limit(page_size)
    )
    items = list(result.scalars().all())
    return PaginatedResponse(
        items=[WorkflowSummaryResponse.model_validate(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/live", response_model=list[LiveWorkflowResponse])
async def live_workflows(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[LiveWorkflowResponse]:
    monitor = ExecutionMonitor(db)
    return [LiveWorkflowResponse(**w) for w in await monitor.get_live_workflows(current_user.tenant_id)]


@router.get("/analytics", response_model=WorkflowAnalyticsResponse)
async def workflow_analytics(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
) -> WorkflowAnalyticsResponse:
    monitor = ExecutionMonitor(db)
    return WorkflowAnalyticsResponse(**await monitor.get_analytics(current_user.tenant_id, days))


@router.get("/agents/activity", response_model=list[AgentActivityResponse])
async def agent_activity(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentActivityResponse]:
    monitor = ExecutionMonitor(db)
    return [AgentActivityResponse(**a) for a in await monitor.get_agent_activity(current_user.tenant_id)]


@router.get("/approvals/pending", response_model=list[ApprovalItemResponse])
async def pending_approvals(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApprovalItemResponse]:
    manager = ApprovalManager(db)
    return [ApprovalItemResponse(**a) for a in await manager.list_pending(current_user.tenant_id)]


@router.get("/approvals/history", response_model=list[ApprovalItemResponse])
async def approval_history(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApprovalItemResponse]:
    manager = ApprovalManager(db)
    return [ApprovalItemResponse(**a) for a in await manager.list_history(current_user.tenant_id)]


@router.websocket("/live/stream")
async def workflow_live_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        payload = decode_token(token)
        tenant_id = str(payload["tenant_id"])
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    redis = None
    pubsub = None
    try:
        import redis.asyncio as aioredis
        from backend.core.config import settings

        redis = aioredis.from_url(str(settings.REDIS_URL), decode_responses=True)
        pubsub = redis.pubsub()
        channel = f"{LIVE_CHANNEL}:{tenant_id}"
        await pubsub.subscribe(channel)

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])
            else:
                await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if pubsub:
            await pubsub.unsubscribe()
            await pubsub.close()
        if redis:
            await redis.close()


@router.get("/live/events")
async def workflow_live_sse(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    async def event_generator():
        import redis.asyncio as aioredis
        from backend.core.config import settings

        redis = aioredis.from_url(str(settings.REDIS_URL), decode_responses=True)
        pubsub = redis.pubsub()
        channel = f"{LIVE_CHANNEL}:{current_user.tenant_id}"
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()
            await redis.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowDetailResponse:
    return await _load_workflow_detail(db, workflow_id, current_user.tenant_id)


@router.get("/{workflow_id}/transparency", response_model=WorkflowTransparencyResponse)
async def get_workflow_transparency(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowTransparencyResponse:
    svc = WorkflowTransparencyService(db)
    try:
        manifest = await svc.build_for_workflow(workflow_id, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkflowTransparencyResponse(**manifest)


@router.get("/{workflow_id}/graph", response_model=WorkflowGraphResponse)
async def get_workflow_graph(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    replay: bool = False,
) -> WorkflowGraphResponse:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == current_user.tenant_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps_result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.step_order)
    )
    steps = list(steps_result.scalars().all())
    visualizer = WorkflowVisualizer()

    if replay:
        logs_result = await db.execute(
            select(WorkflowLog).where(WorkflowLog.workflow_id == workflow_id).order_by(WorkflowLog.created_at)
        )
        logs = [
            {
                "step_id": str(l.step_id) if l.step_id else None,
                "agent_name": l.agent_name,
                "reasoning_summary": l.reasoning_summary,
                "action": l.action,
            }
            for l in logs_result.scalars().all()
        ]
        step_name_map = {str(s.id): s.step_name for s in steps}
        for log in logs:
            if log["step_id"]:
                log["step_name"] = step_name_map.get(log["step_id"])
        graph = visualizer.build_replay_graph(workflow, steps, logs)
    else:
        graph = visualizer.build_graph(workflow, steps)

    return WorkflowGraphResponse(**graph)


@router.get("/{workflow_id}/timeline", response_model=list[TimelineEntry])
async def get_workflow_timeline(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TimelineEntry]:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == current_user.tenant_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps_result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.step_order)
    )
    steps = list(steps_result.scalars().all())

    events_result = await db.execute(
        select(WorkflowEventRecord)
        .where(WorkflowEventRecord.workflow_id == workflow_id)
        .order_by(WorkflowEventRecord.created_at)
    )
    events = list(events_result.scalars().all())

    logs_result = await db.execute(
        select(WorkflowLog).where(WorkflowLog.workflow_id == workflow_id)
    )
    logs = list(logs_result.scalars().all())

    builder = TimelineBuilder()
    return [TimelineEntry(**entry) for entry in builder.build(workflow, steps, events, logs)]


@router.get("/{workflow_id}/logs", response_model=list[WorkflowLogResponse])
async def get_workflow_logs(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkflowLogResponse]:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == current_user.tenant_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")

    logs_result = await db.execute(
        select(WorkflowLog)
        .where(WorkflowLog.workflow_id == workflow_id, WorkflowLog.tenant_id == current_user.tenant_id)
        .order_by(WorkflowLog.created_at)
    )
    return [WorkflowLogResponse.model_validate(l) for l in logs_result.scalars().all()]


@router.post("", response_model=WorkflowSummaryResponse, status_code=201)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowSummaryResponse:
    engine = _get_engine(db)
    try:
        workflow = await engine.create_workflow_record(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            workflow_type=request.workflow_type,
            name=request.name,
            input_data=request.input_data,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkflowSummaryResponse.model_validate(workflow)


@router.post("/{workflow_id}/execute", status_code=202)
async def execute_workflow(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    engine = _get_engine(db)
    try:
        return await engine.execute_workflow(workflow_id, current_user.tenant_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/retry", status_code=202)
async def retry_workflow(
    request: WorkflowRetryRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    engine = _get_engine(db)
    try:
        return await engine.retry_workflow(
            request.workflow_id,
            current_user.tenant_id,
            current_user.id,
            request.from_step,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cancel")
async def cancel_workflow(
    request: WorkflowCancelRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    engine = _get_engine(db)
    try:
        state = await engine.cancel_workflow(
            request.workflow_id, current_user.tenant_id, current_user.id
        )
        return {"workflow_id": str(request.workflow_id), "status": state.value}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workflow_id}/cancel")
async def cancel_workflow_by_id(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    engine = _get_engine(db)
    try:
        state = await engine.cancel_workflow(workflow_id, current_user.tenant_id, current_user.id)
        return {"workflow_id": str(workflow_id), "status": state.value}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
