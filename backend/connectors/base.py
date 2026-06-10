from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ConnectorType(StrEnum):
    MCP = "mcp"
    REST = "rest"
    DATABASE = "database"
    FILE = "file"
    TALLY = "tally"


class ConnectorStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ConnectorConfig:
    name: str
    connector_type: ConnectorType
    endpoint: str | None = None
    credentials: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 3


@dataclass
class ConnectorResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    name: str = "base_connector"
    connector_type: ConnectorType = ConnectorType.MCP
    description: str = ""
    version: str = "1.0.0"

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.status = ConnectorStatus.DISCONNECTED
        self._tools: list[MCPToolDefinition] = []

    @abstractmethod
    async def connect(self) -> ConnectorResult:
        """Establish connection to the external service."""

    @abstractmethod
    async def disconnect(self) -> ConnectorResult:
        """Close connection to the external service."""

    @abstractmethod
    async def health_check(self) -> ConnectorResult:
        """Verify connector is operational."""

    @abstractmethod
    async def list_tools(self) -> list[MCPToolDefinition]:
        """List available MCP tools (for MCP connectors)."""

    @abstractmethod
    async def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> ConnectorResult:
        """Invoke a specific tool on the connected service."""

    async def execute(self, action: str, params: dict[str, Any]) -> ConnectorResult:
        if self.status != ConnectorStatus.CONNECTED:
            connect_result = await self.connect()
            if not connect_result.success:
                return connect_result
        return await self.invoke_tool(action, params)

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.connector_type.value,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "tools": [{"name": t.name, "description": t.description} for t in self._tools],
        }
