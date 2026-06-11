from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AccountingConnectorType(StrEnum):
    TALLY_XML = "tally_xml"
    TALLY_ODBC = "tally_odbc"
    FILE_SYNC = "file_sync"
    FUTURE_ERP = "future_erp"


class AccountingConnectorStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class AccountingConnectorConfig:
    name: str
    connector_type: AccountingConnectorType
    endpoint: str | None = None
    company_name: str | None = None
    credentials: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    timeout_seconds: int = 30


@dataclass
class AccountingConnectorResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    confidence: float | None = None
    reasoning: str | None = None
    source: str | None = None


class BaseAccountingConnector(ABC):
    """Universal accounting connector — ERP-agnostic interface."""

    name: str = "base_accounting"
    connector_type: AccountingConnectorType = AccountingConnectorType.FUTURE_ERP
    description: str = ""
    version: str = "1.0.0"
    priority: int = 99

    def __init__(self, config: AccountingConnectorConfig):
        self.config = config
        self.status = AccountingConnectorStatus.DISCONNECTED

    @abstractmethod
    async def connect(self) -> AccountingConnectorResult:
        """Establish connection to the accounting system."""

    @abstractmethod
    async def disconnect(self) -> AccountingConnectorResult:
        """Close connection."""

    @abstractmethod
    async def health_check(self) -> AccountingConnectorResult:
        """Verify connector operational status."""

    @abstractmethod
    async def discover_companies(self) -> AccountingConnectorResult:
        """Discover companies/books in the accounting system."""

    @abstractmethod
    async def import_masters(self, entity_types: list[str], company_name: str | None = None) -> AccountingConnectorResult:
        """Import master data: ledgers, groups, stock items, units."""

    @abstractmethod
    async def import_transactions(
        self, entity_types: list[str], company_name: str | None = None, from_date: str | None = None
    ) -> AccountingConnectorResult:
        """Import vouchers, inventory, outstanding."""

    @abstractmethod
    async def export_report(self, report_type: str, company_name: str | None = None) -> AccountingConnectorResult:
        """Export reports: trial balance, P&L, balance sheet, GST."""

    @abstractmethod
    async def export_voucher(self, voucher_data: dict[str, Any], company_name: str | None = None) -> AccountingConnectorResult:
        """Export a single voucher to the accounting system."""

    async def execute(self, action: str, params: dict[str, Any]) -> AccountingConnectorResult:
        if self.status != AccountingConnectorStatus.CONNECTED:
            connect_result = await self.connect()
            if not connect_result.success:
                return connect_result

        action_map = {
            "discover_companies": lambda: self.discover_companies(),
            "import_masters": lambda: self.import_masters(
                params.get("entity_types", ["ledgers"]), params.get("company_name")
            ),
            "import_transactions": lambda: self.import_transactions(
                params.get("entity_types", ["vouchers"]),
                params.get("company_name"),
                params.get("from_date"),
            ),
            "export_report": lambda: self.export_report(params.get("report_type", "trial_balance"), params.get("company_name")),
            "export_voucher": lambda: self.export_voucher(params.get("voucher_data", {}), params.get("company_name")),
            "health_check": lambda: self.health_check(),
        }
        handler = action_map.get(action)
        if handler is None:
            return AccountingConnectorResult(success=False, error=f"Unknown action: {action}")
        return await handler()

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.connector_type.value,
            "description": self.description,
            "version": self.version,
            "priority": self.priority,
            "status": self.status.value,
        }
