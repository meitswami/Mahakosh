"""Central data loading for all intelligence modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.twin.repository import TwinRepository
from backend.models.approval import ApprovalQueue
from backend.models.voucher import VoucherDraft


@dataclass
class IntelligenceDataContext:
    """Loads tenant-scoped data once per intelligence request."""

    tenant_id: UUID
    db: AsyncSession
    vouchers: list[dict] = field(default_factory=list)
    parties: list[dict] = field(default_factory=list)
    outstanding: list[dict] = field(default_factory=list)
    ledgers: list[dict] = field(default_factory=list)
    stock_items: list[dict] = field(default_factory=list)
    voucher_drafts: list[dict] = field(default_factory=list)
    pending_approvals: int = 0
    open_data_issues: int = 0
    avg_quality_score: float = 0.0
    _loaded: bool = False

    async def load(self) -> IntelligenceDataContext:
        if self._loaded:
            return self
        repo = TwinRepository(self.db)
        self.vouchers = await repo.get_twin_dicts(self.tenant_id, "voucher")
        self.parties = await repo.get_twin_dicts(self.tenant_id, "party")
        self.outstanding = await repo.get_twin_dicts(self.tenant_id, "outstanding")
        self.ledgers = await repo.get_twin_dicts(self.tenant_id, "ledger")
        self.stock_items = await repo.get_twin_dicts(self.tenant_id, "stock_item")

        if not self.vouchers:
            self.voucher_drafts = await self._load_voucher_drafts()

        overview = await repo.get_overview(self.tenant_id)
        self.open_data_issues = overview.get("open_issues", 0)
        self.avg_quality_score = overview.get("avg_quality_score", 0.0)

        pending = await self.db.execute(
            select(func.count()).select_from(ApprovalQueue).where(
                ApprovalQueue.tenant_id == self.tenant_id,
                ApprovalQueue.status == "pending",
            )
        )
        self.pending_approvals = pending.scalar() or 0
        self._loaded = True
        return self

    async def _load_voucher_drafts(self) -> list[dict]:
        result = await self.db.execute(
            select(VoucherDraft).where(VoucherDraft.tenant_id == self.tenant_id)
        )
        drafts = []
        for v in result.scalars().all():
            drafts.append({
                "id": str(v.id),
                "voucher_type": v.voucher_type,
                "voucher_number": v.voucher_number,
                "voucher_date": v.voucher_date.isoformat() if v.voucher_date else None,
                "party_name": v.party_name,
                "party_gstin": v.party_gstin,
                "subtotal": float(v.subtotal or 0),
                "cgst_amount": float(v.cgst_amount or 0),
                "sgst_amount": float(v.sgst_amount or 0),
                "igst_amount": float(v.igst_amount or 0),
                "total_amount": float(v.total_amount or 0),
                "status": v.status,
            })
        return drafts

    @property
    def all_vouchers(self) -> list[dict]:
        return self.vouchers if self.vouchers else self.voucher_drafts

    @property
    def sales_vouchers(self) -> list[dict]:
        from backend.intelligence.analytics.aggregators import filter_vouchers_by_type
        return filter_vouchers_by_type(self.all_vouchers, "sales", "sale")

    @property
    def purchase_vouchers(self) -> list[dict]:
        from backend.intelligence.analytics.aggregators import filter_vouchers_by_type
        return filter_vouchers_by_type(self.all_vouchers, "purchase", "buy")

    @property
    def receivables(self) -> list[dict]:
        return [o for o in self.outstanding if (o.get("outstanding_type") or "receivable") == "receivable"]

    @property
    def payables(self) -> list[dict]:
        return [o for o in self.outstanding if o.get("outstanding_type") == "payable"]
