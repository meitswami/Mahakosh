from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from backend.connectors.accounting.base.types import (
    AccountingConnectorType,
    CompanyInfo,
    ConnectorOperationResult,
    ConnectorStatus,
    ExportEntityType,
    ImportEntityType,
    LedgerInfo,
    StockItemInfo,
    SyncMode,
    VoucherExportFormat,
)


class BaseAccountingConnector(ABC):
    """Universal accounting connector — not tied to a specific ERP version."""

    connector_type: AccountingConnectorType
    name: str = "base_accounting"
    description: str = ""
    version: str = "1.0.0"
    priority: int = 99
    supported_erp_systems: list[str] = []

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.status = ConnectorStatus.DISCONNECTED

    @abstractmethod
    async def connect(self) -> ConnectorOperationResult:
        """Establish connection to the accounting system."""

    @abstractmethod
    async def disconnect(self) -> ConnectorOperationResult:
        """Close connection."""

    @abstractmethod
    async def health_check(self) -> ConnectorOperationResult:
        """Verify connector operational status."""

    @abstractmethod
    async def discover_companies(self) -> ConnectorOperationResult:
        """Discover companies / books in the accounting system."""

    @abstractmethod
    async def import_entities(
        self,
        entity_type: ImportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        """Import master or transactional data."""

    @abstractmethod
    async def export_entities(
        self,
        entity_type: ExportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        """Export reports or transactional data."""

    @abstractmethod
    async def export_voucher(
        self,
        voucher_data: dict[str, Any],
        company_name: str | None = None,
        export_format: VoucherExportFormat = VoucherExportFormat.TALLY_XML,
    ) -> ConnectorOperationResult:
        """Export a single voucher to the accounting system."""

    async def sync(
        self,
        sync_type: str,
        mode: SyncMode = SyncMode.MANUAL,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        """Default sync delegates to import_entities for master data sync."""
        entity_map = {
            "full": ImportEntityType.LEDGERS,
            "ledgers": ImportEntityType.LEDGERS,
            "items": ImportEntityType.STOCK_ITEMS,
            "vouchers": ImportEntityType.VOUCHERS,
            "outstanding": ImportEntityType.OUTSTANDING,
        }
        entity = entity_map.get(sync_type, ImportEntityType.LEDGERS)
        company = (options or {}).get("company_name")
        return await self.import_entities(entity, company_name=company, options=options)

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connector_type": self.connector_type.value,
            "description": self.description,
            "version": self.version,
            "priority": self.priority,
            "status": self.status.value,
            "supported_erp_systems": self.supported_erp_systems,
        }

    def _ensure_connected(self) -> ConnectorOperationResult | None:
        if self.status != ConnectorStatus.CONNECTED:
            return ConnectorOperationResult(
                success=False,
                error=f"Connector {self.name} is not connected (status={self.status.value})",
            )
        return None

    @staticmethod
    def companies_to_dict(companies: list[CompanyInfo]) -> list[dict[str, Any]]:
        return [
            {
                "name": c.name,
                "financial_year": c.financial_year,
                "books_begin_from": c.books_begin_from.isoformat() if c.books_begin_from else None,
                "books_status": c.books_status,
                "voucher_count": c.voucher_count,
                "ledger_count": c.ledger_count,
                "inventory_count": c.inventory_count,
                "metadata": c.metadata,
            }
            for c in companies
        ]

    @staticmethod
    def ledgers_to_dict(ledgers: list[LedgerInfo]) -> list[dict[str, Any]]:
        return [
            {
                "name": l.name,
                "parent_group": l.parent_group,
                "ledger_type": l.ledger_type,
                "opening_balance": float(l.opening_balance),
                "gstin": l.gstin,
                "pan": l.pan,
                "address": l.address,
                "metadata": l.metadata,
            }
            for l in ledgers
        ]

    @staticmethod
    def items_to_dict(items: list[StockItemInfo]) -> list[dict[str, Any]]:
        return [
            {
                "name": i.name,
                "unit": i.unit,
                "hsn_code": i.hsn_code,
                "gst_rate": float(i.gst_rate) if i.gst_rate is not None else None,
                "opening_stock": float(i.opening_stock),
                "rate": float(i.rate) if i.rate is not None else None,
                "category": i.category,
                "metadata": i.metadata,
            }
            for i in items
        ]
