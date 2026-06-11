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


class FutureERPConnector(BaseAccountingConnector):
    """Priority-4 connector — extensible stub for Busy, Marg, ERPNext, Zoho Books."""

    connector_type = AccountingConnectorType.FUTURE_ERP
    name = "future_erp"
    description = "Universal ERP connector framework for Busy, Marg, ERPNext, Zoho Books"
    version = "1.0.0"
    priority = 4
    supported_erp_systems = ["Busy", "Marg ERP", "ERPNext", "Zoho Books", "Custom ERP"]

    ERP_CONFIG_KEYS = {
        "busy": {"api_base": "http://localhost:8080", "auth_type": "api_key"},
        "marg": {"api_base": "http://localhost:8090", "auth_type": "token"},
        "erpnext": {"api_base": "http://localhost:8000/api", "auth_type": "api_key"},
        "zoho_books": {"api_base": "https://books.zoho.com/api/v3", "auth_type": "oauth2"},
    }

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.erp_system = config.get("erp_system", "custom")
        self.api_base = config.get("api_base", "")
        self.credentials = config.get("credentials", {})

    async def connect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.CONNECTING
        erp_defaults = self.ERP_CONFIG_KEYS.get(self.erp_system, {})
        if not self.api_base:
            self.api_base = erp_defaults.get("api_base", "")

        self.status = ConnectorStatus.CONNECTED
        return ConnectorOperationResult(
            success=True,
            data={
                "erp_system": self.erp_system,
                "api_base": self.api_base,
                "auth_type": erp_defaults.get("auth_type", "custom"),
                "ready": False,
                "message": f"FutureERP connector configured for {self.erp_system}. Implement ERP-specific adapter when credentials are provided.",
            },
        )

    async def disconnect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.DISCONNECTED
        return ConnectorOperationResult(success=True)

    async def health_check(self) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=True,
            data={
                "erp_system": self.erp_system,
                "configured": bool(self.api_base),
                "status": "framework_ready",
            },
        )

    async def discover_companies(self) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=True,
            data={"companies": [], "count": 0, "erp_system": self.erp_system},
            warnings=[f"Company discovery for {self.erp_system} requires ERP-specific adapter configuration"],
        )

    async def import_entities(
        self,
        entity_type: ImportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=False,
            error=f"Import via {self.erp_system} not yet configured. Provide api_base and credentials.",
        )

    async def export_entities(
        self,
        entity_type: ExportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=False,
            error=f"Export via {self.erp_system} not yet configured.",
        )

    async def export_voucher(
        self,
        voucher_data: dict[str, Any],
        company_name: str | None = None,
        export_format: VoucherExportFormat = VoucherExportFormat.JSON,
    ) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=True,
            data={"voucher": voucher_data, "format": export_format.value, "erp_system": self.erp_system},
            warnings=[f"Voucher queued for {self.erp_system} — configure adapter for live export"],
        )


accounting_connector_registry.register(FutureERPConnector)
