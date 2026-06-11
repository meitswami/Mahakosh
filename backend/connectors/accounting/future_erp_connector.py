"""Future ERP connector stub — Busy, Marg, ERPNext, Zoho Books."""

from __future__ import annotations

from typing import Any

from backend.connectors.accounting.base.base_accounting_connector import (
    AccountingConnectorConfig,
    AccountingConnectorResult,
    AccountingConnectorStatus,
    AccountingConnectorType,
    BaseAccountingConnector,
)

SUPPORTED_ERPS = ("busy", "marg", "erpnext", "zoho")


class FutureERPConnector(BaseAccountingConnector):
    name = "future_erp"
    connector_type = AccountingConnectorType.FUTURE_ERP
    description = "Stub connector for Busy, Marg, ERPNext, Zoho Books"
    version = "0.1.0"
    priority = 99

    def __init__(self, config: AccountingConnectorConfig):
        super().__init__(config)
        self.erp_system = config.options.get("erp_system", "erpnext")

    async def connect(self) -> AccountingConnectorResult:
        if self.erp_system not in SUPPORTED_ERPS:
            return AccountingConnectorResult(
                success=False,
                error=f"ERP system '{self.erp_system}' not yet implemented. Supported: {', '.join(SUPPORTED_ERPS)}",
            )
        self.status = AccountingConnectorStatus.CONNECTED
        return AccountingConnectorResult(
            success=True,
            data={"erp_system": self.erp_system, "status": "stub_ready"},
            reasoning=f"{self.erp_system.title()} connector registered — implementation pending",
            source="future_erp",
        )

    async def disconnect(self) -> AccountingConnectorResult:
        self.status = AccountingConnectorStatus.DISCONNECTED
        return AccountingConnectorResult(success=True, data={"disconnected": True})

    async def health_check(self) -> AccountingConnectorResult:
        return AccountingConnectorResult(success=True, data={"healthy": True, "mode": "stub"})

    async def discover_companies(self) -> AccountingConnectorResult:
        return AccountingConnectorResult(success=True, data={"companies": []}, reasoning="Stub — no companies")

    async def import_masters(self, entity_types: list[str], company_name: str | None = None) -> AccountingConnectorResult:
        return AccountingConnectorResult(
            success=True,
            data={et: [] for et in entity_types},
            reasoning=f"Stub import for {self.erp_system}",
            source="future_erp",
        )

    async def import_transactions(self, entity_types: list[str], company_name: str | None = None, from_date: str | None = None) -> AccountingConnectorResult:
        return AccountingConnectorResult(success=True, data={et: [] for et in entity_types}, source="future_erp")

    async def export_report(self, report_type: str, company_name: str | None = None) -> AccountingConnectorResult:
        return AccountingConnectorResult(
            success=False,
            error=f"Export not implemented for {self.erp_system}",
            source="future_erp",
        )

    async def export_voucher(self, voucher_data: dict[str, Any], company_name: str | None = None) -> AccountingConnectorResult:
        return AccountingConnectorResult(
            success=False,
            error=f"Voucher export not implemented for {self.erp_system}",
            source="future_erp",
        )
