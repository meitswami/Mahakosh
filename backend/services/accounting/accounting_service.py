from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.connectors.accounting.register  # noqa: F401 — register connectors
from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.base.types import ExportEntityType, ImportEntityType, SyncMode
from backend.connectors.accounting.draft.draft_engine import VoucherDraftEngine
from backend.connectors.accounting.exports.export_engine import ExportEngine
from backend.connectors.accounting.imports.import_engine import ImportEngine
from backend.connectors.accounting.intelligence.gst_intelligence import GSTIntelligence
from backend.connectors.accounting.intelligence.item_intelligence import ItemIntelligence
from backend.connectors.accounting.intelligence.ledger_intelligence import LedgerIntelligence
from backend.connectors.accounting.twin.service import TwinService
from backend.connectors.accounting.validation.validator import AccountingValidator
from backend.models.accounting import (
    AccountingConnector,
    AccountingValidation,
    ItemMapping,
    LedgerMapping,
    SyncJob,
    SyncLog,
    TallyCompany,
    VoucherExport,
)
from backend.models.customer import Customer
from backend.models.item import Item
from backend.models.ledger import Ledger
from backend.models.vendor import Vendor
from backend.models.voucher import VoucherDraft, VoucherLine


class AccountingService:
    """Orchestrates the universal accounting connector layer."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sync_engine = SyncEngine(db)
        self.import_engine = ImportEngine(db)
        self.export_engine = ExportEngine(db)
        self.ledger_intel = LedgerIntelligence(db)
        self.item_intel = ItemIntelligence(db)
        self.gst_intel = GSTIntelligence(db)
        self.twin_service = TwinService(db)

    async def list_connector_types(self) -> list[dict]:
        return accounting_connector_registry.list_connectors()

    async def list_connectors(self, tenant_id: UUID) -> list[AccountingConnector]:
        result = await self.db.execute(
            select(AccountingConnector)
            .where(AccountingConnector.tenant_id == tenant_id)
            .order_by(AccountingConnector.priority)
        )
        return list(result.scalars().all())

    async def get_connector(self, tenant_id: UUID, connector_id: UUID) -> AccountingConnector | None:
        result = await self.db.execute(
            select(AccountingConnector).where(
                AccountingConnector.id == connector_id,
                AccountingConnector.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def connect(
        self,
        tenant_id: UUID,
        user_id: UUID,
        name: str,
        connector_type: str,
        config: dict[str, Any],
        priority: int = 1,
    ) -> dict[str, Any]:
        connector_instance = accounting_connector_registry.create_instance(connector_type, config)
        result = await connector_instance.connect()

        record = AccountingConnector(
            tenant_id=tenant_id,
            name=name,
            connector_type=connector_type,
            status="connected" if result.success else "error",
            config=config,
            priority=priority,
            last_connected_at=datetime.now(timezone.utc) if result.success else None,
            created_by=user_id,
            metadata_={"health": result.data},
        )
        self.db.add(record)
        await self.db.flush()

        if result.success and result.data.get("companies"):
            pass
        elif result.success:
            discover = await connector_instance.discover_companies()
            if discover.success:
                await self._persist_companies(tenant_id, record.id, discover.data.get("companies", []))

        await connector_instance.disconnect()
        return {
            "connector_id": str(record.id),
            "success": result.success,
            "status": record.status,
            "data": result.data,
            "error": result.error,
        }

    async def _persist_companies(self, tenant_id: UUID, connector_id: UUID, companies: list[dict]) -> int:
        count = 0
        for company_data in companies:
            name = company_data.get("name")
            if not name:
                continue
            existing = await self.db.execute(
                select(TallyCompany).where(
                    TallyCompany.tenant_id == tenant_id,
                    TallyCompany.connector_id == connector_id,
                    TallyCompany.name == name,
                )
            )
            if existing.scalar_one_or_none():
                continue
            books_from = company_data.get("books_begin_from")
            if isinstance(books_from, str):
                try:
                    books_from = date.fromisoformat(books_from)
                except ValueError:
                    books_from = None
            company = TallyCompany(
                tenant_id=tenant_id,
                connector_id=connector_id,
                name=name,
                financial_year=company_data.get("financial_year"),
                books_begin_from=books_from,
                books_status=company_data.get("books_status"),
                voucher_count=company_data.get("voucher_count", 0),
                ledger_count=company_data.get("ledger_count", 0),
                inventory_count=company_data.get("inventory_count", 0),
            )
            self.db.add(company)
            count += 1
        await self.db.flush()
        return count

    async def sync(
        self,
        tenant_id: UUID,
        connector_id: UUID,
        sync_type: str,
        mode: str,
        user_id: UUID,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connector = await self.get_connector(tenant_id, connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}
        return await self.sync_engine.run_sync(
            connector, sync_type, SyncMode(mode), options, user_id
        )

    async def import_data(
        self,
        tenant_id: UUID,
        connector_id: UUID,
        entity_type: str,
        company_name: str | None = None,
        persist: bool = True,
        options: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        connector = await self.get_connector(tenant_id, connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}
        try:
            entity = ImportEntityType(entity_type)
        except ValueError:
            return {"success": False, "error": f"Invalid entity type: {entity_type}"}
        return await self.import_engine.import_from_connector(
            connector, entity, company_name, options, persist, user_id=user_id
        )

    async def export_data(
        self,
        tenant_id: UUID,
        connector_id: UUID,
        entity_type: str,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connector = await self.get_connector(tenant_id, connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}
        try:
            entity = ExportEntityType(entity_type)
        except ValueError:
            return {"success": False, "error": f"Invalid export type: {entity_type}"}
        return await self.export_engine.export_report(connector, entity, company_name, options)

    async def export_voucher(
        self,
        tenant_id: UUID,
        connector_id: UUID,
        voucher_draft_id: UUID,
        user_id: UUID,
        company_id: UUID | None = None,
    ) -> dict[str, Any]:
        connector = await self.get_connector(tenant_id, connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        voucher = await self.db.execute(
            select(VoucherDraft).where(
                VoucherDraft.id == voucher_draft_id,
                VoucherDraft.tenant_id == tenant_id,
            )
        )
        draft = voucher.scalar_one_or_none()
        if not draft:
            return {"success": False, "error": "Voucher draft not found"}
        if draft.status not in ("approved", "draft"):
            return {"success": False, "error": f"Voucher status '{draft.status}' not eligible for export"}

        lines_result = await self.db.execute(
            select(VoucherLine).where(VoucherLine.voucher_id == draft.id)
        )
        lines = lines_result.scalars().all()
        voucher_data = {
            "voucher_type": draft.voucher_type,
            "voucher_number": draft.voucher_number,
            "voucher_date": draft.voucher_date.isoformat(),
            "party_name": draft.party_name,
            "party_gstin": draft.party_gstin,
            "narration": draft.narration,
            "subtotal": float(draft.subtotal),
            "cgst_amount": float(draft.cgst_amount),
            "sgst_amount": float(draft.sgst_amount),
            "igst_amount": float(draft.igst_amount),
            "total_amount": float(draft.total_amount),
            "lines": [
                {
                    "ledger": l.description,
                    "debit": float(l.amount) if l.amount > 0 else 0,
                    "credit": 0,
                    "amount": float(l.amount),
                }
                for l in lines
            ],
        }
        return await self.export_engine.export_voucher(
            connector, voucher_data, voucher_draft_id, company_id, user_id
        )

    async def list_companies(self, tenant_id: UUID, connector_id: UUID | None = None) -> list[TallyCompany]:
        query = select(TallyCompany).where(TallyCompany.tenant_id == tenant_id)
        if connector_id:
            query = query.where(TallyCompany.connector_id == connector_id)
        result = await self.db.execute(query.order_by(TallyCompany.name))
        return list(result.scalars().all())

    async def list_ledgers(self, tenant_id: UUID, page: int = 1, page_size: int = 20) -> tuple[list[Ledger], int]:
        count = await self.db.execute(
            select(func.count()).select_from(Ledger).where(Ledger.tenant_id == tenant_id)
        )
        total = count.scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Ledger).where(Ledger.tenant_id == tenant_id).offset(offset).limit(page_size).order_by(Ledger.name)
        )
        return list(result.scalars().all()), total

    async def list_items(self, tenant_id: UUID, page: int = 1, page_size: int = 20) -> tuple[list[Item], int]:
        count = await self.db.execute(
            select(func.count()).select_from(Item).where(Item.tenant_id == tenant_id)
        )
        total = count.scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Item).where(Item.tenant_id == tenant_id).offset(offset).limit(page_size).order_by(Item.name)
        )
        return list(result.scalars().all()), total

    async def list_vouchers(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20, status: str | None = None
    ) -> tuple[list[VoucherDraft], int]:
        base_filter = [VoucherDraft.tenant_id == tenant_id]
        if status:
            base_filter.append(VoucherDraft.status == status)
        count = await self.db.execute(
            select(func.count()).select_from(VoucherDraft).where(*base_filter)
        )
        total = count.scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(VoucherDraft).where(*base_filter).offset(offset).limit(page_size).order_by(VoucherDraft.created_at.desc())
        )
        return list(result.scalars().all()), total

    async def list_vendors(self, tenant_id: UUID) -> list[Vendor]:
        result = await self.db.execute(select(Vendor).where(Vendor.tenant_id == tenant_id).order_by(Vendor.name))
        return list(result.scalars().all())

    async def list_customers(self, tenant_id: UUID) -> list[Customer]:
        result = await self.db.execute(select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.name))
        return list(result.scalars().all())

    async def create_voucher_draft(self, tenant_id: UUID, user_id: UUID, data: dict[str, Any]) -> VoucherDraft:
        draft_data = VoucherDraftEngine.generate(data)
        voucher = VoucherDraft(
            tenant_id=tenant_id,
            voucher_type=draft_data["voucher_type"],
            voucher_date=date.fromisoformat(draft_data["voucher_date"])
            if isinstance(draft_data["voucher_date"], str)
            else draft_data["voucher_date"],
            party_name=draft_data.get("party_name"),
            party_gstin=draft_data.get("party_gstin"),
            subtotal=Decimal(str(draft_data.get("subtotal", 0))),
            cgst_amount=Decimal(str(draft_data.get("cgst_amount", 0))),
            sgst_amount=Decimal(str(draft_data.get("sgst_amount", 0))),
            igst_amount=Decimal(str(draft_data.get("igst_amount", 0))),
            total_amount=Decimal(str(draft_data.get("total_amount", 0))),
            status="draft",
            narration=draft_data.get("narration"),
            created_by=user_id,
        )
        self.db.add(voucher)
        await self.db.flush()

        for idx, line in enumerate(draft_data.get("lines", []), 1):
            self.db.add(VoucherLine(
                tenant_id=tenant_id,
                voucher_id=voucher.id,
                line_number=idx,
                description=line.get("ledger", ""),
                amount=Decimal(str(line.get("amount", line.get("debit", 0) or line.get("credit", 0)))),
            ))
        await self.db.flush()
        return voucher

    async def validate_voucher(self, tenant_id: UUID, voucher_id: UUID) -> AccountingValidation:
        result = await self.db.execute(
            select(VoucherDraft).where(VoucherDraft.id == voucher_id, VoucherDraft.tenant_id == tenant_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise ValueError("Voucher not found")

        voucher_data = {
            "voucher_type": draft.voucher_type,
            "party_name": draft.party_name,
            "party_gstin": draft.party_gstin,
            "subtotal": float(draft.subtotal),
            "cgst_amount": float(draft.cgst_amount),
            "sgst_amount": float(draft.sgst_amount),
            "igst_amount": float(draft.igst_amount),
        }
        validation = AccountingValidator.validate_voucher_draft(voucher_data)
        record = AccountingValidation(
            tenant_id=tenant_id,
            entity_type="voucher_draft",
            entity_id=voucher_id,
            validation_type="pre_export",
            status="completed",
            is_valid=validation.is_valid,
            issues=[{"code": i.code, "message": i.message, "severity": i.severity} for i in validation.issues],
            checks_passed=validation.checks_passed,
            confidence=validation.confidence,
            reasoning=validation.reasoning,
            validated_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def confirm_ledger_mapping(
        self, tenant_id: UUID, connector_id: UUID, external_name: str, ledger_id: UUID, match_data: dict
    ) -> LedgerMapping:
        mapping = LedgerMapping(
            tenant_id=tenant_id,
            connector_id=connector_id,
            ledger_id=ledger_id,
            external_name=external_name,
            match_type=match_data.get("match_type", "exact"),
            confidence=match_data.get("confidence", 100),
            reasoning=match_data.get("reasoning"),
            source=match_data.get("source"),
            is_confirmed=True,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping

    async def confirm_item_mapping(
        self, tenant_id: UUID, connector_id: UUID, external_name: str, item_id: UUID, match_data: dict
    ) -> ItemMapping:
        mapping = ItemMapping(
            tenant_id=tenant_id,
            connector_id=connector_id,
            item_id=item_id,
            external_name=external_name,
            match_type=match_data.get("match_type", "exact"),
            confidence=match_data.get("confidence", 100),
            reasoning=match_data.get("reasoning"),
            source=match_data.get("source"),
            is_confirmed=True,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping

    async def get_sync_dashboard(self, tenant_id: UUID) -> dict[str, Any]:
        connectors = await self.list_connectors(tenant_id)
        companies = await self.list_companies(tenant_id)
        pending_exports = await self.db.execute(
            select(func.count()).select_from(VoucherExport).where(
                VoucherExport.tenant_id == tenant_id,
                VoucherExport.status == "pending",
            )
        )
        failed_jobs = await self.db.execute(
            select(SyncJob).where(SyncJob.tenant_id == tenant_id, SyncJob.status == "failed")
            .order_by(SyncJob.created_at.desc()).limit(5)
        )
        recent_logs = await self.db.execute(
            select(SyncLog).where(SyncLog.tenant_id == tenant_id)
            .order_by(SyncLog.created_at.desc()).limit(20)
        )
        return {
            "connectors": len(connectors),
            "connected_companies": len(companies),
            "pending_exports": pending_exports.scalar() or 0,
            "last_sync": max(
                (c.last_sync_at.isoformat() for c in connectors if c.last_sync_at),
                default=None,
            ),
            "failed_jobs": [
                {"id": str(j.id), "name": j.name, "status": j.status, "sync_type": j.sync_type}
                for j in failed_jobs.scalars().all()
            ],
            "recent_logs": [
                {"level": l.level, "message": l.message, "created_at": l.created_at.isoformat()}
                for l in recent_logs.scalars().all()
            ],
        }

    async def get_overview(self, tenant_id: UUID) -> dict[str, Any]:
        ledger_count = await self.db.execute(
            select(func.count()).select_from(Ledger).where(Ledger.tenant_id == tenant_id)
        )
        item_count = await self.db.execute(
            select(func.count()).select_from(Item).where(Item.tenant_id == tenant_id)
        )
        voucher_count = await self.db.execute(
            select(func.count()).select_from(VoucherDraft).where(VoucherDraft.tenant_id == tenant_id)
        )
        mapping_count = await self.db.execute(
            select(func.count()).select_from(LedgerMapping).where(LedgerMapping.tenant_id == tenant_id)
        )
        dashboard = await self.get_sync_dashboard(tenant_id)
        twin_overview = await self.twin_service.get_overview(tenant_id)
        return {
            "ledger_count": ledger_count.scalar() or 0,
            "item_count": item_count.scalar() or 0,
            "voucher_count": voucher_count.scalar() or 0,
            "mapping_count": mapping_count.scalar() or 0,
            "connector_types": accounting_connector_registry.list_connectors(),
            "twin": twin_overview,
            **dashboard,
        }

    async def get_twin_overview(self, tenant_id: UUID) -> dict[str, Any]:
        overview = await self.twin_service.get_overview(tenant_id)
        ledger_cleanups = await self.ledger_intel.suggest_cleanups(tenant_id)
        item_cleanups = await self.item_intel.suggest_cleanups(tenant_id)
        gst_cleanups = await self.gst_intel.suggest_cleanups(tenant_id)
        return {
            **overview,
            "suggestions": ledger_cleanups + item_cleanups + gst_cleanups,
            "gst_liability": await self.gst_intel.liability_from_twin(tenant_id),
        }

    async def list_twin_objects(
        self,
        tenant_id: UUID,
        object_type: str,
        page: int = 1,
        page_size: int = 20,
        connector_id: UUID | None = None,
    ) -> tuple[list, int]:
        return await self.twin_service.list_objects(tenant_id, object_type, page, page_size, connector_id)

    async def list_twin_issues(
        self,
        tenant_id: UUID,
        status: str = "open",
        severity: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        return await self.twin_service.list_issues(tenant_id, status, severity, page, page_size)

    async def run_twin_normalization(
        self,
        tenant_id: UUID,
        connector_id: UUID | None,
        entity_types: list[str],
        user_id: UUID,
    ) -> dict[str, Any]:
        return await self.twin_service.run_normalization_job(tenant_id, connector_id, entity_types, user_id)

    async def resolve_twin_issue(
        self,
        tenant_id: UUID,
        issue_id: UUID,
        user_id: UUID,
        resolution: str,
    ) -> dict[str, Any]:
        return await self.twin_service.resolve_issue(tenant_id, issue_id, user_id, resolution)

    async def merge_twin_duplicate(
        self,
        tenant_id: UUID,
        source_id: UUID,
        target_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        return await self.twin_service.merge_duplicate(tenant_id, source_id, target_id, user_id)
