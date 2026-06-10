from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from backend.agents.base.types import AgentEventType


@dataclass
class AgentEvent:
    event_type: AgentEventType
    tenant_id: UUID
    source_agent: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["tenant_id"] = str(self.tenant_id)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentEvent":
        return cls(
            event_type=AgentEventType(data["event_type"]),
            tenant_id=UUID(data["tenant_id"]),
            source_agent=data["source_agent"],
            payload=data.get("payload", {}),
            event_id=data.get("event_id", str(uuid4())),
            timestamp=data.get("timestamp", datetime.now(UTC).isoformat()),
            correlation_id=data.get("correlation_id"),
        )


@dataclass
class AgentMessage:
    message_id: str
    from_agent: str
    to_agent: str
    tenant_id: UUID
    message_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    reply_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "tenant_id": str(self.tenant_id),
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
        }
