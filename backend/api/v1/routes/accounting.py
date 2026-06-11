from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole
from backend.models.accounting import ItemMapping, LedgerMapping, SyncJob
from backend.schemas.accounting import (
    AccountingOverviewResponse,
    ConfirmMappingRequest,
    ConnectRequest,
    ConnectResponse,
    ConnectorResponse,
    ExportRequest,
    ExportVoucherRequest,
    ImportRequest,
    ItemResponse,
    LedgerResponse,
    MappingResponse,
    MatchRequest,
    MatchResultResponse,
    MergeDuplicateRequest,
    NormalizeTwinRequest,
    ResolveIssueRequest,
    SyncJobResponse,
    SyncRequest,
    TallyCompanyResponse,
    TwinIssueResponse,
    TwinObjectResponse,
    TwinOverviewResponse,
    ValidationResponse,
    VoucherDraftRequest,
    VoucherResponse,
)
from backend.platform.feature_gate import require_feature
from backend.schemas.common import PaginatedResponse
from backend.services.accounting.accounting_service import AccountingService

router = APIRouter(dependencies=[Depends(require_feature("tally"))])


def _service(db: AsyncSession) -> AccountingService:
    return AccountingService(db)


@router.get("/overview", response_model=AccountingOverviewResponse)
async def accounting_overview(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountingOverviewResponse:
    service = _service(db)
    data = await service.get_overview(current_user.tenant_id)
    return AccountingOverviewResponse(**data)


@router.get("/connector-types")
async def list_connector_types(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    return {"connectors": await service.list_connector_types()}


@router.get("/connectors", response_model=list[ConnectorResponse])
async def list_connectors(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConnectorResponse]:
    service = _service(db)
    connectors = await service.list_connectors(current_user.tenant_id)
    return [ConnectorResponse.model_validate(c) for c in connectors]


@router.post("/connect", response_model=ConnectResponse, status_code=201)
async def connect_accounting(
    request: ConnectRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConnectResponse:
    service = _service(db)
    result = await service.connect(
        current_user.tenant_id,
        current_user.id,
        request.name,
        request.connector_type,
        request.config,
        request.priority,
    )
    await db.commit()
    return ConnectResponse(**result)


@router.post("/sync")
async def sync_accounting(
    request: SyncRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.sync(
        current_user.tenant_id,
        request.connector_id,
        request.sync_type,
        request.mode,
        current_user.id,
        request.options,
    )
    await db.commit()
    return result


@router.post("/import")
async def import_accounting(
    request: ImportRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.import_data(
        current_user.tenant_id,
        request.connector_id,
        request.entity_type,
        request.company_name,
        request.persist,
        request.options,
        user_id=current_user.id,
    )
    await db.commit()
    return result


@router.post("/export")
async def export_accounting(
    request: ExportRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.export_data(
        current_user.tenant_id,
        request.connector_id,
        request.entity_type,
        request.company_name,
        request.options,
    )
    return result


@router.post("/vouchers/{voucher_id}/export")
async def export_voucher(
    voucher_id: UUID,
    request: ExportVoucherRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.export_voucher(
        current_user.tenant_id,
        request.connector_id,
        voucher_id,
        current_user.id,
        request.company_id,
    )
    await db.commit()
    return result


@router.get("/companies", response_model=list[TallyCompanyResponse])
async def list_companies(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    connector_id: UUID | None = None,
) -> list[TallyCompanyResponse]:
    service = _service(db)
    companies = await service.list_companies(current_user.tenant_id, connector_id)
    return [TallyCompanyResponse.model_validate(c) for c in companies]


@router.get("/ledgers", response_model=PaginatedResponse[LedgerResponse])
async def list_ledgers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[LedgerResponse]:
    service = _service(db)
    items, total = await service.list_ledgers(current_user.tenant_id, page, page_size)
    return PaginatedResponse(
        items=[LedgerResponse.model_validate(l) for l in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/items", response_model=PaginatedResponse[ItemResponse])
async def list_items(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ItemResponse]:
    service = _service(db)
    items, total = await service.list_items(current_user.tenant_id, page, page_size)
    return PaginatedResponse(
        items=[ItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/vouchers", response_model=PaginatedResponse[VoucherResponse])
async def list_vouchers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
) -> PaginatedResponse[VoucherResponse]:
    service = _service(db)
    items, total = await service.list_vouchers(current_user.tenant_id, page, page_size, status)
    return PaginatedResponse(
        items=[VoucherResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.post("/vouchers/draft", response_model=VoucherResponse, status_code=201)
async def create_voucher_draft(
    request: VoucherDraftRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoucherResponse:
    service = _service(db)
    voucher = await service.create_voucher_draft(
        current_user.tenant_id,
        current_user.id,
        request.model_dump(),
    )
    await db.commit()
    return VoucherResponse.model_validate(voucher)


@router.post("/vouchers/{voucher_id}/validate", response_model=ValidationResponse)
async def validate_voucher(
    voucher_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationResponse:
    service = _service(db)
    try:
        record = await service.validate_voucher(current_user.tenant_id, voucher_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    await db.commit()
    return ValidationResponse.model_validate(record)


@router.post("/vouchers/{voucher_id}/approve", status_code=202)
async def approve_voucher(
    voucher_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MANAGER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from backend.models.voucher import VoucherDraft

    result = await db.execute(
        select(VoucherDraft).where(
            VoucherDraft.id == voucher_id,
            VoucherDraft.tenant_id == current_user.tenant_id,
        )
    )
    voucher = result.scalar_one_or_none()
    if not voucher:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voucher not found")
    voucher.status = "approved"
    await db.commit()
    return {"voucher_id": str(voucher_id), "status": "approved"}


@router.get("/vendors")
async def list_vendors(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    vendors = await service.list_vendors(current_user.tenant_id)
    return {
        "vendors": [{"id": str(v.id), "name": v.name, "gstin": v.gstin} for v in vendors],
        "total": len(vendors),
    }


@router.get("/customers")
async def list_customers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    customers = await service.list_customers(current_user.tenant_id)
    return {
        "customers": [{"id": str(c.id), "name": c.name, "gstin": c.gstin} for c in customers],
        "total": len(customers),
    }


@router.get("/mappings/ledgers", response_model=list[MappingResponse])
async def list_ledger_mappings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    connector_id: UUID | None = None,
) -> list[MappingResponse]:
    query = select(LedgerMapping).where(LedgerMapping.tenant_id == current_user.tenant_id)
    if connector_id:
        query = query.where(LedgerMapping.connector_id == connector_id)
    result = await db.execute(query.order_by(LedgerMapping.external_name))
    return [MappingResponse.model_validate(m) for m in result.scalars().all()]


@router.get("/mappings/items", response_model=list[MappingResponse])
async def list_item_mappings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    connector_id: UUID | None = None,
) -> list[MappingResponse]:
    query = select(ItemMapping).where(ItemMapping.tenant_id == current_user.tenant_id)
    if connector_id:
        query = query.where(ItemMapping.connector_id == connector_id)
    result = await db.execute(query.order_by(ItemMapping.external_name))
    return [MappingResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/mappings/ledgers/match", response_model=list[MatchResultResponse])
async def match_ledgers(
    request: MatchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MatchResultResponse]:
    service = _service(db)
    results = await service.ledger_intel.suggest_mappings(
        current_user.tenant_id, request.external_names, request.connector_id
    )
    return [MatchResultResponse(**r) for r in results]


@router.post("/mappings/items/match", response_model=list[MatchResultResponse])
async def match_items(
    request: MatchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MatchResultResponse]:
    service = _service(db)
    results = await service.item_intel.suggest_mappings(
        current_user.tenant_id, request.external_names, request.connector_id
    )
    return [MatchResultResponse(**r) for r in results]


@router.post("/mappings/ledgers/confirm", response_model=MappingResponse, status_code=201)
async def confirm_ledger_mapping(
    request: ConfirmMappingRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MappingResponse:
    service = _service(db)
    mapping = await service.confirm_ledger_mapping(
        current_user.tenant_id,
        request.connector_id,
        request.external_name,
        request.internal_id,
        request.model_dump(),
    )
    await db.commit()
    return MappingResponse.model_validate(mapping)


@router.post("/mappings/items/confirm", response_model=MappingResponse, status_code=201)
async def confirm_item_mapping(
    request: ConfirmMappingRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MappingResponse:
    service = _service(db)
    mapping = await service.confirm_item_mapping(
        current_user.tenant_id,
        request.connector_id,
        request.external_name,
        request.internal_id,
        request.model_dump(),
    )
    await db.commit()
    return MappingResponse.model_validate(mapping)


@router.get("/sync/dashboard", response_model=AccountingOverviewResponse)
async def sync_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountingOverviewResponse:
    service = _service(db)
    data = await service.get_sync_dashboard(current_user.tenant_id)
    overview = await service.get_overview(current_user.tenant_id)
    return AccountingOverviewResponse(**{**overview, **data})


@router.get("/sync/jobs", response_model=list[SyncJobResponse])
async def list_sync_jobs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    connector_id: UUID | None = None,
) -> list[SyncJobResponse]:
    query = select(SyncJob).where(SyncJob.tenant_id == current_user.tenant_id)
    if connector_id:
        query = query.where(SyncJob.connector_id == connector_id)
    result = await db.execute(query.order_by(SyncJob.created_at.desc()).limit(50))
    return [SyncJobResponse.model_validate(j) for j in result.scalars().all()]


@router.post("/intelligence/gst/validate")
async def validate_gst(
    invoice_data: dict,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    return service.gst_intel.validate_invoice(invoice_data)


@router.get("/twin/overview", response_model=TwinOverviewResponse)
async def twin_overview(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TwinOverviewResponse:
    service = _service(db)
    data = await service.get_twin_overview(current_user.tenant_id)
    return TwinOverviewResponse(**data)


@router.get("/twin/ledgers", response_model=PaginatedResponse[TwinObjectResponse])
async def twin_ledgers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    connector_id: UUID | None = None,
) -> PaginatedResponse[TwinObjectResponse]:
    service = _service(db)
    items, total = await service.list_twin_objects(
        current_user.tenant_id, "ledger", page, page_size, connector_id
    )
    return PaginatedResponse(
        items=[TwinObjectResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/twin/items", response_model=PaginatedResponse[TwinObjectResponse])
async def twin_items(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    connector_id: UUID | None = None,
) -> PaginatedResponse[TwinObjectResponse]:
    service = _service(db)
    items, total = await service.list_twin_objects(
        current_user.tenant_id, "stock_item", page, page_size, connector_id
    )
    return PaginatedResponse(
        items=[TwinObjectResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/twin/parties", response_model=PaginatedResponse[TwinObjectResponse])
async def twin_parties(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    connector_id: UUID | None = None,
) -> PaginatedResponse[TwinObjectResponse]:
    service = _service(db)
    items, total = await service.list_twin_objects(
        current_user.tenant_id, "party", page, page_size, connector_id
    )
    return PaginatedResponse(
        items=[TwinObjectResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/twin/vouchers", response_model=PaginatedResponse[TwinObjectResponse])
async def twin_vouchers(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    connector_id: UUID | None = None,
) -> PaginatedResponse[TwinObjectResponse]:
    service = _service(db)
    items, total = await service.list_twin_objects(
        current_user.tenant_id, "voucher", page, page_size, connector_id
    )
    return PaginatedResponse(
        items=[TwinObjectResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/twin/issues", response_model=PaginatedResponse[TwinIssueResponse])
async def twin_issues(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str = Query("open"),
    severity: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[TwinIssueResponse]:
    service = _service(db)
    items, total = await service.list_twin_issues(
        current_user.tenant_id, status, severity, page, page_size
    )
    return PaginatedResponse(
        items=[TwinIssueResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.post("/twin/normalize")
async def normalize_twin(
    request: NormalizeTwinRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.run_twin_normalization(
        current_user.tenant_id,
        request.connector_id,
        request.entity_types,
        current_user.id,
    )
    await db.commit()
    return result


@router.post("/twin/resolve-issue")
async def resolve_twin_issue(
    request: ResolveIssueRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.resolve_twin_issue(
        current_user.tenant_id,
        request.issue_id,
        current_user.id,
        request.resolution,
    )
    await db.commit()
    return result


@router.post("/twin/merge-duplicate")
async def merge_twin_duplicate(
    request: MergeDuplicateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _service(db)
    result = await service.merge_twin_duplicate(
        current_user.tenant_id,
        request.source_id,
        request.target_id,
        current_user.id,
    )
    await db.commit()
    return result
