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
from backend.connectors.accounting.xml.engine import TallyXMLEngine


class TallyXMLConnector(BaseAccountingConnector):
    """Priority-1 connector — Tally Prime / ERP 9 / Silver / Gold via XML HTTP gateway."""

    connector_type = AccountingConnectorType.TALLY_XML
    name = "tally_xml"
    description = "Tally XML import/export via HTTP gateway (port 9000)"
    version = "1.0.0"
    priority = 1
    supported_erp_systems = [
        "Tally Prime",
        "Tally ERP 9",
        "Tally Silver",
        "Tally Gold",
    ]

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        host = config.get("host", "localhost")
        port = int(config.get("port", 9000))
        timeout = float(config.get("timeout_seconds", 30))
        self._engine = TallyXMLEngine(host=host, port=port, timeout=timeout)
        self._company_name = config.get("company_name")

    async def connect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.CONNECTING
        health = await self._engine.health_check()
        if health.get("healthy"):
            self.status = ConnectorStatus.CONNECTED
            return ConnectorOperationResult(
                success=True,
                data={"endpoint": health.get("endpoint"), "tally_version": health.get("tally_version")},
            )
        self.status = ConnectorStatus.ERROR
        return ConnectorOperationResult(success=False, error=health.get("error", "Tally XML connection failed"))

    async def disconnect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.DISCONNECTED
        return ConnectorOperationResult(success=True, data={"disconnected": True})

    async def health_check(self) -> ConnectorOperationResult:
        health = await self._engine.health_check()
        return ConnectorOperationResult(
            success=health.get("healthy", False),
            data=health,
            error=health.get("error"),
        )

    async def discover_companies(self) -> ConnectorOperationResult:
        err = self._ensure_connected()
        if err:
            connect = await self.connect()
            if not connect.success:
                return connect

        ok, companies, error = await self._engine.discover_companies()
        if not ok:
            return ConnectorOperationResult(success=False, error=error)
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
        err = self._ensure_connected()
        if err:
            connect = await self.connect()
            if not connect.success:
                return connect

        company = company_name or self._company_name
        opts = options or {}

        if entity_type == ImportEntityType.LEDGERS:
            ok, data, error = await self._engine.import_ledgers(company)
            key, transform = "ledgers", self.ledgers_to_dict
        elif entity_type in (ImportEntityType.STOCK_ITEMS, ImportEntityType.INVENTORY):
            ok, data, error = await self._engine.import_stock_items(company)
            key, transform = "items", self.items_to_dict
        elif entity_type == ImportEntityType.VOUCHERS:
            ok, data, error = await self._engine.import_vouchers(
                company,
                opts.get("from_date"),
                opts.get("to_date"),
            )
            key, transform = "vouchers", lambda x: x
        else:
            return ConnectorOperationResult(
                success=False,
                error=f"Import type {entity_type.value} not supported via Tally XML",
            )

        if not ok:
            return ConnectorOperationResult(success=False, error=error)
        return ConnectorOperationResult(
            success=True,
            data={key: transform(data), "count": len(data), "entity_type": entity_type.value},
        )

    async def export_entities(
        self,
        entity_type: ExportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        err = self._ensure_connected()
        if err:
            connect = await self.connect()
            if not connect.success:
                return connect

        company = company_name or self._company_name
        ok, response, error = await self._engine.export_report(entity_type, company)
        if not ok:
            return ConnectorOperationResult(success=False, error=error)
        return ConnectorOperationResult(
            success=True,
            data={"entity_type": entity_type.value, "xml_response": response, "format": "xml"},
        )

    async def export_voucher(
        self,
        voucher_data: dict[str, Any],
        company_name: str | None = None,
        export_format: VoucherExportFormat = VoucherExportFormat.TALLY_XML,
    ) -> ConnectorOperationResult:
        if export_format == VoucherExportFormat.JSON:
            return ConnectorOperationResult(success=True, data={"voucher": voucher_data, "format": "json"})

        if export_format == VoucherExportFormat.TALLY_XML:
            xml_payload = self._engine.generate_voucher_xml(voucher_data)
            err = self._ensure_connected()
            if err:
                return ConnectorOperationResult(
                    success=True,
                    data={"xml": xml_payload, "format": "tally_xml", "queued": True},
                    warnings=["Tally not connected — XML generated for manual import"],
                )
            ok, _, error = await self._engine.export_voucher(voucher_data)
            if not ok:
                return ConnectorOperationResult(
                    success=True,
                    data={"xml": xml_payload, "format": "tally_xml", "queued": True},
                    warnings=[error or "Export queued — Tally rejected live import"],
                )
            return ConnectorOperationResult(
                success=True,
                data={"xml": xml_payload, "format": "tally_xml", "exported": True},
            )

        return ConnectorOperationResult(success=False, error=f"Unsupported export format: {export_format.value}")


accounting_connector_registry.register(TallyXMLConnector)
