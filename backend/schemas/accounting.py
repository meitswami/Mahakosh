from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import BaseSchema


class ConnectRequest(BaseModel):
    name: str
    connector_type: str
    config: dict = Field(default_factory=dict)
    priority: int = 1


class ConnectResponse(BaseModel):
    connector_id: UUID
    success: bool
    status: str
    data: dict = Field(default_factory=dict)
    error: str | None = None


class SyncRequest(BaseModel):
    connector_id: UUID
    sync_type: str = "ledgers"
    mode: str = "manual"
    options: dict = Field(default_factory=dict)


class ImportRequest(BaseModel):
    connector_id: UUID
    entity_type: str
    company_name: str | None = None
    persist: bool = True
    options: dict = Field(default_factory=dict)


class ExportRequest(BaseModel):
    connector_id: UUID
    entity_type: str
    company_name: str | None = None
    options: dict = Field(default_factory=dict)


class ExportVoucherRequest(BaseModel):
    connector_id: UUID
    company_id: UUID | None = None


class VoucherDraftRequest(BaseModel):
    document_type: str = "purchase_invoice"
    vendor_name: str | None = None
    customer_name: str | None = None
    party_name: str | None = None
    amount: float | None = None
    subtotal: float | None = None
    gst_rate: float = 18.0
    gstin: str | None = None
    party_gstin: str | None = None
    inter_state: bool = False
    narration: str | None = None
    line_items: list[dict] = Field(default_factory=list)


class ConfirmMappingRequest(BaseModel):
    connector_id: UUID
    external_name: str
    internal_id: UUID
    match_type: str = "exact"
    confidence: float = 100.0
    reasoning: str | None = None
    source: str | None = None


class MatchRequest(BaseModel):
    external_names: list[str]
    connector_id: UUID | None = None


class ConnectorResponse(BaseSchema):
    id: UUID
    name: str
    connector_type: str
    status: str
    config: dict
    priority: int
    last_connected_at: datetime | None
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TallyCompanyResponse(BaseSchema):
    id: UUID
    connector_id: UUID
    name: str
    financial_year: str | None
    books_begin_from: date | None
    books_status: str | None
    voucher_count: int
    ledger_count: int
    inventory_count: int
    is_active: bool


class LedgerResponse(BaseSchema):
    id: UUID
    name: str
    parent_group: str | None
    ledger_type: str
    opening_balance: float
    current_balance: float
    gstin: str | None
    tally_ledger_name: str | None
    is_active: bool


class ItemResponse(BaseSchema):
    id: UUID
    name: str
    sku: str | None
    hsn_code: str | None
    unit: str
    gst_rate: float | None
    category: str | None
    tally_stock_item_name: str | None
    is_active: bool


class VoucherResponse(BaseSchema):
    id: UUID
    voucher_type: str
    voucher_number: str | None
    voucher_date: date
    party_name: str | None
    party_gstin: str | None
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float
    status: str
    narration: str | None
    created_at: datetime


class MappingResponse(BaseSchema):
    id: UUID
    connector_id: UUID
    external_name: str
    match_type: str
    confidence: float
    reasoning: str | None
    is_confirmed: bool
    ledger_id: UUID | None = None
    item_id: UUID | None = None


class SyncJobResponse(BaseSchema):
    id: UUID
    connector_id: UUID
    name: str
    sync_type: str
    trigger_mode: str
    status: str
    last_run_at: datetime | None
    created_at: datetime


class AccountingOverviewResponse(BaseModel):
    ledger_count: int
    item_count: int
    voucher_count: int
    mapping_count: int
    connectors: int
    connected_companies: int
    pending_exports: int
    last_sync: str | None
    connector_types: list[dict]
    failed_jobs: list[dict]
    recent_logs: list[dict]


class MatchResultResponse(BaseModel):
    external_name: str
    internal_id: str | None
    internal_name: str | None
    match_type: str
    confidence: float
    reasoning: str
    source: str


class ValidationResponse(BaseSchema):
    id: UUID
    entity_type: str
    entity_id: UUID
    validation_type: str
    status: str
    is_valid: bool
    issues: list
    checks_passed: list
    confidence: float | None
    reasoning: str | None


class TwinObjectResponse(BaseSchema):
    id: UUID
    object_type: str
    source_system: str
    source_id: str
    display_name: str
    normalized_fields: dict
    quality_score: float
    issues: list
    normalization_notes: list
    connector_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TwinOverviewResponse(BaseModel):
    object_counts: dict[str, int]
    total_objects: int
    avg_quality_score: float
    open_issues: int
    error_issues: int
    suggestions: list[dict] = Field(default_factory=list)
    gst_liability: dict = Field(default_factory=dict)


class TwinIssueResponse(BaseSchema):
    id: UUID
    twin_object_id: UUID
    issue_type: str
    code: str
    severity: str
    message: str
    suggestion: str | None
    status: str
    created_at: datetime


class NormalizeTwinRequest(BaseModel):
    connector_id: UUID | None = None
    entity_types: list[str] = Field(default_factory=lambda: ["ledger", "stock_item", "party", "voucher"])


class ResolveIssueRequest(BaseModel):
    issue_id: UUID
    resolution: str
    status: str = "resolved"


class MergeDuplicateRequest(BaseModel):
    source_id: UUID
    target_id: UUID
