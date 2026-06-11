from typing import Any

from backend.connectors.accounting.base.connector import BaseAccountingConnector
from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.base.types import (
    AccountingConnectorType,
    ConnectorOperationResult,
    ConnectorStatus,
    ExportEntityType,
    ImportEntityType,
    VoucherExportFormat,
)
from backend.connectors.accounting.odbc.driver import TallyODBCDriver


class TallyODBCConnector(BaseAccountingConnector):
    """Priority-2 connector — Tally via ODBC (Windows + Tally ODBC driver)."""

    connector_type = AccountingConnectorType.TALLY_ODBC
    name = "tally_odbc"
    description = "Tally ODBC connector for direct database queries"
    version = "1.0.0"
    priority = 2
    supported_erp_systems = ["Tally Prime", "Tally ERP 9", "Tally Silver", "Tally Gold"]

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        dsn = config.get("dsn", "TallyODBC64_9000")
        conn_str = config.get("connection_string")
        self._driver = TallyODBCDriver(dsn=dsn, connection_string=conn_str)

    async def connect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.CONNECTING
        ok, error = self._driver.connect()
        if ok:
            self.status = ConnectorStatus.CONNECTED
            return ConnectorOperationResult(success=True, data={"dsn": self._driver.dsn})
        self.status = ConnectorStatus.ERROR
        return ConnectorOperationResult(success=False, error=error)

    async def disconnect(self) -> ConnectorOperationResult:
        self._driver.disconnect()
        self.status = ConnectorStatus.DISCONNECTED
        return ConnectorOperationResult(success=True)

    async def health_check(self) -> ConnectorOperationResult:
        health = self._driver.health_check()
        return ConnectorOperationResult(
            success=health.get("healthy", False),
            data=health,
            error=health.get("error"),
        )

    async def discover_companies(self) -> ConnectorOperationResult:
        if self.status != ConnectorStatus.CONNECTED:
            result = await self.connect()
            if not result.success:
                return result
        companies = self._driver.list_companies()
        return ConnectorOperationResult(
            success=True,
            data={"companies": self.companies_to_dict(companies), "count": len(companies)},
        )

    async def import_entities(
        self,
        entity_type: ImportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        if self.status != ConnectorStatus.CONNECTED:
            result = await self.connect()
            if not result.success:
                return result

        if entity_type == ImportEntityType.LEDGERS:
            data = self._driver.list_ledgers()
            return ConnectorOperationResult(
                success=True,
                data={"ledgers": self.ledgers_to_dict(data), "count": len(data)},
            )
        if entity_type in (ImportEntityType.STOCK_ITEMS, ImportEntityType.INVENTORY):
            data = self._driver.list_stock_items()
            return ConnectorOperationResult(
                success=True,
                data={"items": self.items_to_dict(data), "count": len(data)},
            )
        return ConnectorOperationResult(
            success=False,
            error=f"ODBC import for {entity_type.value} not supported",
        )

    async def export_entities(
        self,
        entity_type: ExportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=False,
            error="ODBC connector is read-only for master data. Use Tally XML for exports.",
        )

    async def export_voucher(
        self,
        voucher_data: dict[str, Any],
        company_name: str | None = None,
        export_format: VoucherExportFormat = VoucherExportFormat.TALLY_XML,
    ) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=False,
            error="Voucher export via ODBC not supported. Use Tally XML connector.",
        )


accounting_connector_registry.register(TallyODBCConnector)
