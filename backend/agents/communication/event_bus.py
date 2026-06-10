import json
from typing import Any, Callable, Awaitable
from uuid import UUID

import structlog

from backend.agents.base.types import AgentEventType
from backend.agents.communication.events import AgentEvent, AgentMessage
from backend.core.config import settings

logger = structlog.get_logger(__name__)

CHANNEL_PREFIX = "mahakosh:agents"
BROADCAST_CHANNEL = f"{CHANNEL_PREFIX}:broadcast"


class AgentEventBus:
    """Redis Pub/Sub event bus with in-process fallback."""

    def __init__(self) -> None:
        self._redis = None
        self._local_handlers: dict[str, list[Callable[[AgentEvent], Awaitable[None]]]] = {}
        self._message_handlers: dict[str, list[Callable[[AgentMessage], Awaitable[None]]]] = {}

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(str(settings.REDIS_URL), decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception as exc:
            logger.warning("redis_unavailable_using_local_bus", error=str(exc))
            return None

    def _channel(self, tenant_id: UUID, event_type: AgentEventType | None = None) -> str:
        base = f"{CHANNEL_PREFIX}:{tenant_id}"
        if event_type:
            return f"{base}:{event_type.value}"
        return base

    async def publish(self, event: AgentEvent) -> None:
        redis = await self._get_redis()
        payload = json.dumps(event.to_dict())
        if redis:
            await redis.publish(self._channel(event.tenant_id), payload)
            await redis.publish(self._channel(event.tenant_id, event.event_type), payload)
            await redis.publish(BROADCAST_CHANNEL, payload)
        for handler in self._local_handlers.get(event.event_type.value, []):
            await handler(event)
        for handler in self._local_handlers.get("*", []):
            await handler(event)
        logger.info("event_published", event_type=event.event_type.value, source=event.source_agent)

    async def send_message(self, message: AgentMessage) -> None:
        redis = await self._get_redis()
        payload = json.dumps(message.to_dict())
        channel = f"{CHANNEL_PREFIX}:msg:{message.tenant_id}:{message.to_agent}"
        if redis:
            await redis.publish(channel, payload)
        for handler in self._message_handlers.get(message.to_agent, []):
            await handler(message)

    def subscribe(
        self,
        event_type: AgentEventType | str,
        handler: Callable[[AgentEvent], Awaitable[None]],
    ) -> None:
        key = event_type.value if isinstance(event_type, AgentEventType) else event_type
        self._local_handlers.setdefault(key, []).append(handler)

    def subscribe_messages(
        self,
        agent_name: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        self._message_handlers.setdefault(agent_name, []).append(handler)

    async def broadcast(self, tenant_id: UUID, source_agent: str, event_type: AgentEventType, payload: dict[str, Any]) -> None:
        event = AgentEvent(
            event_type=event_type,
            tenant_id=tenant_id,
            source_agent=source_agent,
            payload=payload,
        )
        await self.publish(event)


event_bus = AgentEventBus()
