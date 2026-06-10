import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.chat.chat_gateway import ChatGateway
from backend.core.database import async_session_factory, get_db
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.security import decode_token
from backend.models.audit import AuditLog
from backend.schemas.chat import (
    ChatHistoryResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    ChatSessionDetail,
    ChatSessionSummary,
    CitationResponse,
    ReasoningStepResponse,
    SavedQueryRequest,
    TransparencyResponse,
)

router = APIRouter()


def _pipeline_to_response(pipeline) -> ChatQueryResponse:
    return ChatQueryResponse(
        answer=pipeline.answer,
        session_id=pipeline.session_id,
        message_id=str(pipeline.message_id) if pipeline.message_id else None,
        chat_type=pipeline.chat_type.value,
        intent=pipeline.intent.value,
        confidence=pipeline.confidence,
        citations=[CitationResponse(**c) for c in pipeline.citations],
        structured_data=pipeline.structured_data,
        agents_used=pipeline.agents_used,
        reasoning_steps=[ReasoningStepResponse(**s.to_dict()) for s in pipeline.reasoning_steps],
        transparency=TransparencyResponse(**pipeline.transparency) if pipeline.transparency else None,
        query_id=str(pipeline.query_id) if pipeline.query_id else None,
        processing_time_ms=pipeline.processing_time_ms,
        model_used=pipeline.model_used,
    )


async def _audit_chat(db: AsyncSession, user: CurrentUser, action: str, session_id: str | None, query: str) -> None:
    db.add(AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action=action,
        entity_type="chat",
        description=query[:500],
        metadata_={"session_id": session_id},
    ))


@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(
    request: ChatQueryRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatQueryResponse:
    gateway = ChatGateway(db)
    pipeline = await gateway.query(
        message=request.message,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        session_id=request.session_id,
        chat_type=request.chat_type,
    )
    await _audit_chat(db, current_user, "chat_query", pipeline.session_id, request.message)
    return _pipeline_to_response(pipeline)


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatHistoryResponse:
    gateway = ChatGateway(db)
    sessions = await gateway.get_history(current_user.tenant_id, current_user.id)
    return ChatHistoryResponse(
        sessions=[ChatSessionSummary(**s) for s in sessions],
        total=len(sessions),
    )


@router.get("/session/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionDetail:
    gateway = ChatGateway(db)
    session = await gateway.get_session(session_id, current_user.tenant_id, current_user.id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return ChatSessionDetail(**session)


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    gateway = ChatGateway(db)
    deleted = await gateway.delete_session(session_id, current_user.tenant_id, current_user.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    await _audit_chat(db, current_user, "chat_session_delete", str(session_id), "")
    return {"deleted": True, "session_id": str(session_id)}


@router.post("/saved-queries")
async def save_query(
    request: SavedQueryRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from backend.chat.memory_manager import MemoryManager
    mgr = MemoryManager(db)
    sq = await mgr.save_query(
        current_user.tenant_id,
        current_user.id,
        request.name,
        request.query_text,
        request.chat_type,
        filters=request.filters,
    )
    return {"id": str(sq.id), "name": sq.name}


@router.get("/saved-queries")
async def list_saved_queries(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from backend.chat.memory_manager import MemoryManager
    mgr = MemoryManager(db)
    queries = await mgr.list_saved_queries(current_user.tenant_id, current_user.id)
    return {
        "items": [
            {
                "id": str(q.id),
                "name": q.name,
                "query_text": q.query_text,
                "chat_type": q.chat_type,
                "usage_count": q.usage_count,
            }
            for q in queries
        ],
        "total": len(queries),
    }


@router.post("", response_model=ChatQueryResponse, deprecated=True)
async def chat_legacy(
    request: ChatQueryRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatQueryResponse:
    return await chat_query(request, current_user, db)


@router.websocket("/stream")
async def chat_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        payload = decode_token(token)
        tenant_id = UUID(payload["tenant_id"])
        user_id = UUID(payload["sub"])
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            message = data.get("message", "").strip()
            if not message:
                await websocket.send_json({"type": "error", "content": "message is required"})
                continue

            session_id = UUID(data["session_id"]) if data.get("session_id") else None
            chat_type = data.get("chat_type")

            async with async_session_factory() as db:
                gateway = ChatGateway(db)
                async for event in gateway.stream_query(
                    message, tenant_id, user_id, session_id, chat_type
                ):
                    await websocket.send_json(event)
                await db.commit()

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass
