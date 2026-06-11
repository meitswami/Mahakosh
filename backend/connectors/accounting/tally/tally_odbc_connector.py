"""Tally ODBC connector — priority 2 integration via Tally ODBC driver."""

from __future__ import annotations

from typing import Any

from backend.connectors.accounting.base.base_accounting_connector import (
    AccountingConnectorConfig,
    AccountingConnectorResult,
    AccountingConnectorStatus,
    AccountingConnectorType,
    BaseAccountingConnector,
)
from backend.connectors.accounting.imports.import_engine import ImportEngine
from backend.connectors.accounting.odbc.odbc_client import TallyODBCClient


class TallyODBCConnector(BaseAccountingConnector):
    name = "tally_odbc"
    connector_type = AccountingConnectorType.TALLY_ODBC
    description = "Tally ERP integration via ODBC driver"
    version = "1.0.0"
    priority = 2

    def __init__(self, config: AccountingConnectorConfig):
        super().__init__(config)
        self._client = TallyODBCClient(
            dsn=config.options.get("dsn", "TallyODBC64"),
            company=config.company_name,
        )
        self._import_engine = ImportEngine()

    async def connect(self) -> AccountingConnectorResult:
        self.status = AccountingConnectorStatus.CONNECTING
        result = await self._client.connect()
        if result.success:
            self.status = AccountingConnectorStatus.CONNECTED
        else:
            self.status = AccountingConnectorStatus.ERROR
        return result

    async def disconnect(self) -> AccountingConnectorResult:
        result = await self._client.disconnect()
        self.status = AccountingConnectorStatus.DISCONNECTED
        return result

    async def health_check(self) -> AccountingConnectorResult:
        return await self._client.health_check()

    async def discover_companies(self) -> AccountingConnectorResult:
        companies = await self._client.list_companies()
        return AccountingConnectorResult(success=True, data={"companies": companies}, source="tally_odbc")

    async def import_masters(self, entity_types: list[str], company_name: str | None = None) -> AccountingConnectorResult:
        company = company_name or self.config.company_name
        results: dict[str, Any] = {}
        if "ledgers" in entity_types or "groups" in entity_types:
            ledgers = await self._client.query_ledgers(company)
            results["ledgers"] = self._import_engine.normalize_ledgers(ledgers)
        if "stock_items" in entity_types or "items" in entity_types:
            items = await self._client.query_stock_items(company)
            results["stock_items"] = self._import_engine.normalize_stock_items(items)
        if "units" in entity_types:
            results["units"] = await self._client.query_units(company)
        return AccountingConnectorResult(success=True, data=results, source="tally_odbc")

    async def import_transactions(
        self, entity_types: list[str], company_name: str | None = None, from_date: str | None = None
    ) -> AccountingConnectorResult:
        company = company_name or self.config.company_name
        results: dict[str, Any] = {}
        if "vouchers" in entity_types:
            vouchers = await self._client.query_vouchers(company, from_date)
            results["vouchers"] = self._import_engine.normalize_vouchers(vouchers)
        if "outstanding" in entity_types:
            results["outstanding"] = await self._client.query_outstanding(company)
        return AccountingConnectorResult(success=True, data=results, source="tally_odbc")

    async def export_report(self, report_type: str, company_name: str | None = None) -> AccountingConnectorResult:
        company = company_name or self.config.company_name
        report = await self._client.export_report(report_type, company)
        return AccountingConnectorResult(success=True, data=report, source="tally_odbc")

    async def export_voucher(self, voucher_data: dict[str, Any], company_name: str | None = None) -> AccountingConnectorResult:
        from backend.connectors.accounting.xml.xml_engine import TallyXMLEngine

        xml_payload = TallyXMLEngine.voucher(voucher_data)
        return AccountingConnectorResult(
            success=True,
            data={"xml": xml_payload, "mode": "odbc_xml_bridge", "company": company_name},
            reasoning="ODBC connector generates XML for Tally import",
            source="tally_odbc",
        )
