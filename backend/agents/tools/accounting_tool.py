"""Accounting connector tool — agents access Tally/ERP only through this tool."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.exports.export_engine import ExportEngine
from backend.connectors.accounting.validation.validator import AccountingValidator
from backend.services.accounting.accounting_service import AccountingService


class AccountingTool:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._service = AccountingService(db)
        self._export_engine = ExportEngine(db)

    async def list_connectors(self, tenant_id: UUID) -> list[dict[str, Any]]:
        connectors = await self._service.list_connectors(tenant_id)
        return [
            {"id": str(c.id), "name": c.name, "type": c.connector_type, "status": c.status}
            for c in connectors
        ]

    async def discover_companies(self, tenant_id: UUID, connector_id: UUID) -> list[dict[str, Any]]:
        companies = await self._service.list_companies(tenant_id, connector_id)
        return [{"id": str(c.id), "name": c.name, "financial_year": c.financial_year} for c in companies]

    async def create_voucher_draft(self, tenant_id: UUID, user_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        voucher = await self._service.create_voucher_draft(tenant_id, user_id, data)
        return {
            "voucher_id": str(voucher.id),
            "voucher_type": voucher.voucher_type,
            "total_amount": float(voucher.total_amount),
            "status": voucher.status,
        }

    async def prepare_export(
        self, tenant_id: UUID, voucher_data: dict[str, Any], validation_status: str, approval_status: str
    ) -> dict[str, Any]:
        validation = AccountingValidator.validate_voucher_draft(voucher_data)
        if not validation.is_valid:
            return {
                "export_ready": False,
                "reason": validation.reasoning,
                "stage": "validation",
                "validation": AccountingValidator.to_dict(validation),
            }
        if approval_status != "approved":
            return {
                "export_ready": False,
                "reason": f"Approval status: {approval_status}",
                "stage": "approval",
            }
        from backend.connectors.accounting.xml.generator import TallyXMLGenerator

        xml = TallyXMLGenerator.voucher_xml(voucher_data)
        return {"export_ready": True, "xml": xml, "stage": "export"}

    async def export_via_connector(
        self,
        tenant_id: UUID,
        user_id: UUID,
        connector_id: UUID,
        voucher_id: UUID,
    ) -> dict[str, Any]:
        return await self._service.export_voucher(tenant_id, connector_id, voucher_id, user_id)

    async def sync(self, tenant_id: UUID, user_id: UUID, connector_id: UUID, entity_types: list[str]) -> dict[str, Any]:
        return await self._service.sync(
            tenant_id, connector_id, "import", "manual", user_id, {"entity_types": entity_types}
        )

    async def search(self, tenant_id: UUID, query: str) -> dict[str, Any]:
        overview = await self._service.get_overview(tenant_id)
        ledgers, _ = await self._service.list_ledgers(tenant_id, 1, 100)
        ledger_dicts = [
            {
                "id": str(l.id),
                "name": l.name,
                "parent_group": l.parent_group,
                "ledger_type": l.ledger_type,
                "current_balance": float(l.current_balance),
                "gstin": l.gstin,
            }
            for l in ledgers
        ]
        return {
            "query": query,
            "overview": overview,
            "top_customers": await self._service.ledger_intel.suggest_mappings(tenant_id, [], None),
            "receivables": {"total_receivables": sum(float(l.current_balance) for l in ledgers if float(l.current_balance) > 0)},
        }

    def list_available_connector_types(self) -> list[dict[str, Any]]:
        return accounting_connector_registry.list_connectors()
