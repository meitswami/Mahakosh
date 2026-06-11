from uuid import UUID

import structlog

from backend.channels.base.types import ChannelType
from backend.core.config import settings

logger = structlog.get_logger(__name__)

LIMITS = {
    "messages_per_minute": 30,
    "uploads_per_hour": 20,
    "workflow_triggers_per_hour": 10,
}


class ChannelRateLimiter:
    """Redis-backed rate limiting for channel abuse prevention."""

    def __init__(self) -> None:
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

    async def check_message(
        self,
        tenant_id: UUID,
        user_id: UUID,
        channel: ChannelType,
    ) -> tuple[bool, dict]:
        redis = await self._get_redis()
        if not redis:
            return True, {"limited": False}

        key = f"mahakosh:rate:msg:{tenant_id}:{user_id}:{channel.value}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)

        allowed = count <= LIMITS["messages_per_minute"]
        return allowed, {
            "limited": not allowed,
            "count": count,
            "limit": LIMITS["messages_per_minute"],
            "window": "1m",
        }

    async def check_upload(self, tenant_id: UUID, user_id: UUID) -> tuple[bool, dict]:
        redis = await self._get_redis()
        if not redis:
            return True, {"limited": False}

        key = f"mahakosh:rate:upload:{tenant_id}:{user_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 3600)

        allowed = count <= LIMITS["uploads_per_hour"]
        return allowed, {"limited": not allowed, "count": count, "limit": LIMITS["uploads_per_hour"]}

    async def check_workflow_trigger(self, tenant_id: UUID, user_id: UUID) -> tuple[bool, dict]:
        redis = await self._get_redis()
        if not redis:
            return True, {"limited": False}

        key = f"mahakosh:rate:workflow:{tenant_id}:{user_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 3600)

        allowed = count <= LIMITS["workflow_triggers_per_hour"]
        return allowed, {"limited": not allowed, "count": count, "limit": LIMITS["workflow_triggers_per_hour"]}

    async def get_usage(self, tenant_id: UUID, user_id: UUID, channel: ChannelType) -> dict:
        redis = await self._get_redis()
        if not redis:
            return {"messages": 0, "uploads": 0, "workflows": 0}

        msg_key = f"mahakosh:rate:msg:{tenant_id}:{user_id}:{channel.value}"
        upload_key = f"mahakosh:rate:upload:{tenant_id}:{user_id}"
        wf_key = f"mahakosh:rate:workflow:{tenant_id}:{user_id}"

        msg_count = int(await redis.get(msg_key) or 0)
        upload_count = int(await redis.get(upload_key) or 0)
        wf_count = int(await redis.get(wf_key) or 0)

        return {
            "messages_per_minute": {"count": msg_count, "limit": LIMITS["messages_per_minute"]},
            "uploads_per_hour": {"count": upload_count, "limit": LIMITS["uploads_per_hour"]},
            "workflow_triggers_per_hour": {"count": wf_count, "limit": LIMITS["workflow_triggers_per_hour"]},
        }
