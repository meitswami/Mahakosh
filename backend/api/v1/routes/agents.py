from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.agents.implementations  # noqa: F401 — register agents
from backend.agents.memory.task_memory import task_memory
from backend.agents.registry.registry import agent_registry
from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole
from backend.models.approval import ApprovalQueue
from backend.schemas.agents import (
    AgentEventResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentExecutionResponse,
    AgentHealthResponse,
    AgentInfoResponse,
    AgentStatusResponse,
    OrchestratorRequest,
    OrchestratorResponse,
)
from backend.services.agent_execution_service import AgentExecutionService

router = APIRouter()


@router.get("", response_model=list[AgentInfoResponse])
async def list_agents(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[AgentInfoResponse]:
    return [AgentInfoResponse(**agent) for agent in agent_registry.list_agents()]


@router.get("/status", response_model=AgentStatusResponse)
async def agent_status(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentStatusResponse:
    service = AgentExecutionService(db)
    health_records = await service.get_health(current_user.tenant_id)
    health_map = {h.agent_name: h for h in health_records}

    agents = agent_registry.list_agents()
    health_responses = []
    for agent in agents:
        h = health_map.get(agent["name"])
        if h:
            health_responses.append(AgentHealthResponse(
                agent_name=h.agent_name,
                status=h.status,
                healthy=h.success_rate >= 50,
                execution_count=h.execution_count,
                success_rate=h.success_rate,
                average_runtime_ms=h.average_runtime_ms,
                queue_length=h.queue_length,
                last_error=h.last_error,
            ))
        else:
            instance = agent_registry.get_instance(agent["name"])
            report = await instance.health_check()
            health_responses.append(AgentHealthResponse(
                agent_name=report.agent_name,
                status=report.status.value,
                healthy=report.healthy,
                execution_count=report.execution_count,
                success_rate=report.success_rate,
                average_runtime_ms=report.average_runtime_ms,
                queue_length=report.queue_length,
                last_error=report.last_error,
            ))

    active = task_memory.list_active(str(current_user.tenant_id))
    return AgentStatusResponse(
        total_agents=len(agents),
        active_tasks=len(active),
        agents=[AgentInfoResponse(**a) for a in agents],
        health=health_responses,
    )


@router.get("/health", response_model=list[AgentHealthResponse])
async def agent_health(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentHealthResponse]:
    service = AgentExecutionService(db)
    records = await service.get_health(current_user.tenant_id)
    if records:
        return [
            AgentHealthResponse(
                agent_name=r.agent_name,
                status=r.status,
                healthy=r.success_rate >= 50,
                execution_count=r.execution_count,
                success_rate=r.success_rate,
                average_runtime_ms=r.average_runtime_ms,
                queue_length=r.queue_length,
                last_error=r.last_error,
            )
            for r in records
        ]
    return [
        AgentHealthResponse(**h)
        for h in await agent_registry.health_check_all()
    ]


@router.get("/executions", response_model=list[AgentExecutionResponse])
async def list_executions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_name: str | None = None,
    limit: int = 50,
) -> list[AgentExecutionResponse]:
    service = AgentExecutionService(db)
    executions = await service.list_executions(current_user.tenant_id, agent_name, limit)
    return [AgentExecutionResponse.model_validate(e) for e in executions]


@router.get("/events", response_model=list[AgentEventResponse])
async def list_events(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> list[AgentEventResponse]:
    service = AgentExecutionService(db)
    events = await service.list_events(current_user.tenant_id, limit)
    return [AgentEventResponse.model_validate(e) for e in events]


@router.get("/approvals/pending")
async def pending_approvals(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    result = await db.execute(
        select(ApprovalQueue)
        .where(
            ApprovalQueue.tenant_id == current_user.tenant_id,
            ApprovalQueue.status == "pending",
        )
        .order_by(ApprovalQueue.created_at.desc())
        .limit(50)
    )
    items = [
        {
            "id": str(a.id),
            "title": a.title,
            "action": a.action,
            "entity_type": a.entity_type,
            "priority": a.priority,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]
    return {"items": items, "total": len(items)}


@router.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate_task(
    request: OrchestratorRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrchestratorResponse:
    service = AgentExecutionService(db)
    input_data = {
        "task_type": request.task_type,
        "payload": request.payload,
        "execution_mode": request.execution_mode,
    }
    result, execution = await service.run_agent(
        "master_orchestrator",
        input_data,
        current_user.tenant_id,
        current_user.id,
    )
    return OrchestratorResponse(
        success=result.success,
        task_id=result.data.get("task_id"),
        data=result.data,
        confidence=result.confidence,
        processing_time_ms=result.processing_time_ms,
        execution_id=execution.id,
    )


@router.get("/{agent_name}", response_model=AgentInfoResponse)
async def get_agent(
    agent_name: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AgentInfoResponse:
    try:
        agent = agent_registry.get_instance(agent_name)
        return AgentInfoResponse(**agent.get_info())
    except KeyError as exc:
        raise HTTPException(404, f"Agent '{agent_name}' not found") from exc


@router.post("/{agent_name}/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    agent_name: str,
    request: AgentExecuteRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentExecuteResponse:
    try:
        agent_registry.get_instance(agent_name)
    except KeyError as exc:
        raise HTTPException(404, f"Agent '{agent_name}' not found") from exc

    service = AgentExecutionService(db)
    result, execution = await service.run_agent(
        agent_name,
        request.input_data,
        current_user.tenant_id,
        current_user.id,
        model_name=request.model_name,
    )

    return AgentExecuteResponse(
        success=result.success,
        agent_name=agent_name,
        execution_id=execution.id,
        data=result.data,
        confidence=result.confidence,
        confidence_level=result.confidence_level.value,
        reasoning=result.reasoning,
        sources=result.sources,
        error=result.error,
        processing_time_ms=result.processing_time_ms,
    )
