from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.base.registry import channel_registry
from backend.channels.base.types import ChannelType, IncomingMessage, OutgoingMessage
from backend.channels.gateway.gateway import CommunicationGateway
from backend.channels.notification_center import NotificationCenter
from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole
from backend.models.audit import AuditLog
from backend.models.channels import (
    ChannelMessage,
    ChannelSession,
    ChannelUser,
    CommunicationChannel,
)
from backend.schemas.channels import (
    ChannelConnectRequest,
    ChannelDashboardResponse,
    ChannelLinkRequest,
    ChannelMessageResponse,
    ChannelReceiveRequest,
    ChannelResponse,
    ChannelSendRequest,
    ChannelSessionResponse,
    ChannelSummary,
)

router = APIRouter()


def _ensure_channels():
    import backend.channels.register  # noqa: F401


@router.get("/dashboard", response_model=ChannelDashboardResponse)
async def channel_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChannelDashboardResponse:
    _ensure_channels()
    notif_center = NotificationCenter(db)
    dashboard = await notif_center.get_dashboard(current_user.tenant_id)

    channels_result = await db.execute(
        select(CommunicationChannel).where(
            CommunicationChannel.tenant_id == current_user.tenant_id,
            CommunicationChannel.is_active.is_(True),
        )
    )
    channels = list(channels_result.scalars().all())

    msg_count = (await db.execute(
        select(func.count()).select_from(ChannelMessage).where(
            ChannelMessage.tenant_id == current_user.tenant_id
        )
    )).scalar() or 0

    session_count = (await db.execute(
        select(func.count()).select_from(ChannelSession).where(
            ChannelSession.tenant_id == current_user.tenant_id,
            ChannelSession.status == "active",
        )
    )).scalar() or 0

    user_count = (await db.execute(
        select(func.count()).select_from(ChannelUser).where(
            ChannelUser.tenant_id == current_user.tenant_id,
            ChannelUser.is_active.is_(True),
        )
    )).scalar() or 0

    health = []
    for ct in ChannelType:
        try:
            adapter = channel_registry.get(ct)
            health.append(await adapter.health_check())
        except KeyError:
            pass

    from backend.channels.routing.rate_limiter import ChannelRateLimiter
    rate = await ChannelRateLimiter().get_usage(
        current_user.tenant_id, current_user.id, ChannelType.WEBCHAT
    )

    return ChannelDashboardResponse(
        connected_channels=[ChannelSummary.model_validate(c) for c in channels],
        active_sessions=session_count,
        total_messages=msg_count,
        active_users=user_count,
        recent_notifications=dashboard.get("recent_notifications", []),
        channel_health=health,
        rate_limits=rate,
    )


@router.post("/connect", response_model=ChannelSummary, status_code=201)
async def connect_channel(
    request: ChannelConnectRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChannelSummary:
    _ensure_channels()
    channel = CommunicationChannel(
        tenant_id=current_user.tenant_id,
        channel_type=request.channel_type,
        name=request.name,
        config=request.config,
        webhook_url=request.webhook_url,
        status="active",
    )
    db.add(channel)

    if request.webhook_url and request.channel_type == "telegram":
        adapter = channel_registry.get(ChannelType.TELEGRAM)
        result = await adapter.setup_webhook(f"{request.webhook_url}/api/v1/channels/webhook/telegram")
        channel.bot_username = result.get("result", {}).get("username") if isinstance(result.get("result"), dict) else None

    db.add(AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="channel_connected",
        entity_type="communication_channel",
        metadata_={"channel_type": request.channel_type, "name": request.name},
    ))
    await db.flush()
    return ChannelSummary.model_validate(channel)


@router.post("/link")
async def link_channel_user(
    request: ChannelLinkRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    existing = await db.execute(
        select(ChannelUser).where(
            ChannelUser.tenant_id == current_user.tenant_id,
            ChannelUser.channel_type == request.channel_type,
            ChannelUser.external_user_id == request.external_user_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"linked": True, "message": "Already linked"}

    link = ChannelUser(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        channel_type=request.channel_type,
        external_user_id=request.external_user_id,
        external_chat_id=request.external_chat_id,
        external_username=request.external_username,
        linked_at=datetime.now(UTC),
    )
    db.add(link)
    await db.flush()
    return {"linked": True, "channel_user_id": str(link.id)}


@router.post("/send")
async def send_message(
    request: ChannelSendRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    _ensure_channels()
    gateway = CommunicationGateway(db)
    return await gateway.send(
        ChannelType(request.channel_type),
        request.external_chat_id,
        request.message,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        metadata=request.metadata,
    )


@router.post("/receive", response_model=ChannelResponse)
async def receive_message(
    request: ChannelReceiveRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChannelResponse:
    _ensure_channels()
    from backend.channels.base.types import AttachmentType, ChannelAttachment

    attachments = [
        ChannelAttachment(
            filename=a.get("filename", "file"),
            content_type=a.get("content_type", "application/octet-stream"),
            attachment_type=AttachmentType(a.get("attachment_type", "other")),
            size_bytes=a.get("size_bytes", 0),
        )
        for a in request.attachments
    ]

    incoming = IncomingMessage(
        channel=ChannelType(request.channel_type),
        external_user_id=request.external_user_id or str(current_user.id),
        external_chat_id=request.external_chat_id or str(current_user.id),
        text=request.message,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        session_id=request.session_id,
        attachments=attachments,
        metadata=request.metadata,
    )

    gateway = CommunicationGateway(db)
    response = await gateway.receive(incoming)
    await db.commit()
    return ChannelResponse(
        text=response.text,
        session_id=response.session_id,
        chat_session_id=response.chat_session_id,
        transparency=response.transparency,
        citations=response.citations,
        agents_used=response.agents_used,
        processing_time_ms=response.processing_time_ms,
    )


@router.get("/sessions", response_model=list[ChannelSessionResponse])
async def list_sessions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_type: str | None = None,
) -> list[ChannelSessionResponse]:
    query = select(ChannelSession).where(
        ChannelSession.tenant_id == current_user.tenant_id,
        ChannelSession.user_id == current_user.id,
    )
    if channel_type:
        query = query.where(ChannelSession.channel_type == channel_type)
    result = await db.execute(query.order_by(ChannelSession.last_message_at.desc().nullslast()).limit(50))
    return [ChannelSessionResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/messages", response_model=list[ChannelMessageResponse])
async def list_messages(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[ChannelMessageResponse]:
    query = select(ChannelMessage).where(ChannelMessage.tenant_id == current_user.tenant_id)
    if session_id:
        query = query.where(ChannelMessage.session_id == session_id)
    else:
        query = query.where(ChannelMessage.user_id == current_user.id)
    result = await db.execute(query.order_by(ChannelMessage.created_at.desc()).limit(limit))
    return [ChannelMessageResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    _ensure_channels()
    payload = await request.json()
    adapter = channel_registry.get(ChannelType.TELEGRAM)
    incoming = await adapter.parse_webhook(payload)
    if not incoming:
        return {"ok": True}

    gateway = CommunicationGateway(db)
    try:
        response = await gateway.receive(incoming)
        await adapter.send(OutgoingMessage(
            channel=ChannelType.TELEGRAM,
            external_chat_id=incoming.external_chat_id,
            text=response.text,
        ))
        await db.commit()
    except ValueError as exc:
        await adapter.send(OutgoingMessage(
            channel=ChannelType.TELEGRAM,
            external_chat_id=incoming.external_chat_id,
            text=f"Please link your account in Mahakosh: {exc}",
        ))
    return {"ok": True}


@router.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Any:
    from backend.core.config import settings
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    _ensure_channels()
    payload = await request.json()
    adapter = channel_registry.get(ChannelType.WHATSAPP)
    incoming = await adapter.parse_webhook(payload)
    if not incoming:
        return {"status": "ignored"}

    gateway = CommunicationGateway(db)
    try:
        response = await gateway.receive(incoming)
        await adapter.send(OutgoingMessage(
            channel=ChannelType.WHATSAPP,
            external_chat_id=incoming.external_chat_id,
            text=response.text,
        ))
        await db.commit()
    except ValueError:
        pass
    return {"status": "ok"}


@router.post("/webhook/email")
async def email_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    _ensure_channels()
    payload = await request.json()
    adapter = channel_registry.get(ChannelType.EMAIL)
    incoming = await adapter.parse_webhook(payload)
    if not incoming:
        return {"status": "ignored"}

    gateway = CommunicationGateway(db)
    try:
        response = await gateway.receive(incoming)
        await adapter.send(OutgoingMessage(
            channel=ChannelType.EMAIL,
            external_chat_id=incoming.external_chat_id,
            text=response.text,
            metadata={"subject": "Re: " + incoming.metadata.get("subject", "Mahakosh")},
        ))
        await db.commit()
    except ValueError:
        pass
    return {"status": "ok"}


@router.get("/health")
async def channel_health() -> list[dict]:
    _ensure_channels()
    results = []
    for ct in ChannelType:
        try:
            adapter = channel_registry.get(ct)
            results.append(await adapter.health_check())
        except KeyError:
            pass
    return results
