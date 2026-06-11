from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from backend.channels.base.types import (
    ChannelCapabilities,
    ChannelType,
    IncomingMessage,
    OutgoingMessage,
)


class BaseChannelAdapter(ABC):
    """Abstract adapter for omnichannel communication."""

    channel_type: ChannelType

    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """Return supported capabilities for this channel."""

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> dict[str, Any]:
        """Send a message to the external channel."""

    @abstractmethod
    async def parse_webhook(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse an inbound webhook payload into a normalized message."""

    async def verify_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> bool:
        return True

    async def setup_webhook(self, webhook_url: str) -> dict[str, Any]:
        return {"status": "not_configured", "channel": self.channel_type.value}

    async def health_check(self) -> dict[str, Any]:
        return {"channel": self.channel_type.value, "healthy": True}

    def format_approval_keyboard(self, approval_id: str) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "Approve", "callback_data": f"approve:{approval_id}"},
                    {"text": "Reject", "callback_data": f"reject:{approval_id}"},
                    {"text": "Review", "callback_data": f"review:{approval_id}"},
                ]
            ]
        }
