from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class AccountingConnectorType(StrEnum):
    TALLY_XML = "tally_xml"
    TALLY_ODBC = "tally_odbc"
    FILE_SYNC = "file_sync"
    FUTURE_ERP = "future_erp"


class SyncMode(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    FOLDER_WATCH = "folder_watch"
    WORKFLOW = "workflow"


class ImportEntityType(StrEnum):
    LEDGERS = "ledgers"
    GROUPS = "groups"
    STOCK_ITEMS = "stock_items"
    UNITS = "units"
    VOUCHERS = "vouchers"
    INVENTORY = "inventory"
    OUTSTANDING = "outstanding"
    CUSTOMERS = "customers"
    VENDORS = "vendors"


class ExportEntityType(StrEnum):
    SALES = "sales"
    PURCHASES = "purchases"
    LEDGERS = "ledgers"
    STOCK_SUMMARY = "stock_summary"
    TRIAL_BALANCE = "trial_balance"
    PROFIT_LOSS = "profit_loss"
    BALANCE_SHEET = "balance_sheet"
    GST_DATA = "gst_data"
    VOUCHERS = "vouchers"


class VoucherExportFormat(StrEnum):
    TALLY_XML = "tally_xml"
    JSON = "json"
    CSV = "csv"


class ConnectorStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MatchType(StrEnum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    HISTORICAL = "historical"
    AI_ASSISTED = "ai_assisted"
    UNMATCHED = "unmatched"


@dataclass
class ConnectorOperationResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class CompanyInfo:
    name: str
    financial_year: str | None = None
    books_begin_from: date | None = None
    books_status: str | None = None
    voucher_count: int = 0
    ledger_count: int = 0
    inventory_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerInfo:
    name: str
    parent_group: str | None = None
    ledger_type: str = "general"
    opening_balance: Decimal = Decimal("0")
    gstin: str | None = None
    pan: str | None = None
    address: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StockItemInfo:
    name: str
    unit: str = "NOS"
    hsn_code: str | None = None
    gst_rate: Decimal | None = None
    opening_stock: Decimal = Decimal("0")
    rate: Decimal | None = None
    category: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    external_name: str
    internal_id: UUID | None
    internal_name: str | None
    match_type: MatchType
    confidence: float
    reasoning: str
    source: str


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    field: str | None = None


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class SyncJobResult:
    job_id: UUID | None
    status: str
    records_processed: int = 0
    records_failed: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    logs: list[dict[str, Any]] = field(default_factory=list)
