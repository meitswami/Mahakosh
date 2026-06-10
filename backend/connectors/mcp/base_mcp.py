from typing import Any

import httpx

from backend.connectors.base import (
    BaseConnector,
    ConnectorResult,
    ConnectorStatus,
    ConnectorType,
    MCPToolDefinition,
)


class BaseMCPConnector(BaseConnector):
    connector_type = ConnectorType.MCP

    async def connect(self) -> ConnectorResult:
        self.status = ConnectorStatus.CONNECTING
        try:
            health = await self.health_check()
            if health.success:
                self.status = ConnectorStatus.CONNECTED
                self._tools = await self.list_tools()
            else:
                self.status = ConnectorStatus.ERROR
            return health
        except Exception as exc:
            self.status = ConnectorStatus.ERROR
            return ConnectorResult(success=False, error=str(exc))

    async def disconnect(self) -> ConnectorResult:
        self.status = ConnectorStatus.DISCONNECTED
        self._tools = []
        return ConnectorResult(success=True, data={"disconnected": True})

    async def health_check(self) -> ConnectorResult:
        if not self.config.endpoint:
            return ConnectorResult(success=False, error="MCP endpoint not configured")

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(f"{self.config.endpoint}/health")
            if response.status_code == 200:
                return ConnectorResult(success=True, data=response.json())
            return ConnectorResult(
                success=False,
                error=f"Health check failed with status {response.status_code}",
            )

    async def list_tools(self) -> list[MCPToolDefinition]:
        if not self.config.endpoint:
            return []

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(f"{self.config.endpoint}/tools")
            if response.status_code != 200:
                return []
            tools_data = response.json().get("tools", [])
            return [
                MCPToolDefinition(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                )
                for t in tools_data
            ]

    async def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> ConnectorResult:
        if not self.config.endpoint:
            return ConnectorResult(success=False, error="MCP endpoint not configured")

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.endpoint}/tools/{tool_name}/invoke",
                json={"arguments": arguments},
            )
            if response.status_code == 200:
                return ConnectorResult(success=True, data=response.json())
            return ConnectorResult(
                success=False,
                error=f"Tool invocation failed: {response.text}",
            )
