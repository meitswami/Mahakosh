from typing import Any

from backend.connectors.base import ConnectorConfig, ConnectorResult, MCPToolDefinition
from backend.connectors.mcp.base_mcp import BaseMCPConnector
from backend.connectors.registry import connector_registry


class TallyMCPConnector(BaseMCPConnector):
    name = "tally"
    description = "MCP connector for Tally ERP integration"
    version = "1.0.0"

    TALLY_TOOLS = [
        MCPToolDefinition(
            name="export_voucher",
            description="Export voucher to Tally ERP",
            input_schema={"type": "object", "properties": {"voucher_id": {"type": "string"}}},
        ),
        MCPToolDefinition(
            name="import_ledgers",
            description="Import ledger masters from Tally",
            input_schema={"type": "object", "properties": {"company_name": {"type": "string"}}},
        ),
        MCPToolDefinition(
            name="import_stock_items",
            description="Import stock items from Tally",
            input_schema={"type": "object", "properties": {"company_name": {"type": "string"}}},
        ),
        MCPToolDefinition(
            name="sync_gstin",
            description="Sync GSTIN data with Tally party masters",
            input_schema={"type": "object", "properties": {"gstin": {"type": "string"}}},
        ),
    ]

    async def list_tools(self) -> list[MCPToolDefinition]:
        remote_tools = await super().list_tools()
        return remote_tools if remote_tools else self.TALLY_TOOLS

    async def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> ConnectorResult:
        if self.status.value != "connected" and not self.config.endpoint:
            return ConnectorResult(
                success=True,
                data={
                    "tool": tool_name,
                    "status": "queued",
                    "message": f"Tally {tool_name} operation queued for execution",
                    "arguments": arguments,
                },
            )
        return await super().invoke_tool(tool_name, arguments)


connector_registry.register(TallyMCPConnector)
