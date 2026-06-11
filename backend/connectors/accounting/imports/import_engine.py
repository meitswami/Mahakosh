from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.base.types import ImportEntityType
from backend.connectors.accounting.twin.service import TwinService
from backend.models.accounting import AccountingConnector
from backend.models.customer import Customer
from backend.models.item import Item
from backend.models.ledger import Ledger
from backend.models.vendor import Vendor


class ImportEngine:
    """Import ledgers, items, vouchers from accounting connectors into Mahakosh.

    Pipeline: raw connector data → normalizer → twin objects → persist → knowledge
    Legacy domain tables (Ledger, Item, etc.) are still updated for backward compatibility.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_service = TwinService(db)

    async def import_from_connector(
        self,
        connector_record: AccountingConnector,
        entity_type: ImportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
        persist: bool = True,
        user_id: UUID | None = None,
        sync_job_id: UUID | None = None,
    ) -> dict[str, Any]:
        connector = accounting_connector_registry.create_instance(
            connector_record.connector_type,
            connector_record.config,
        )
        await connector.connect()
        result = await connector.import_entities(entity_type, company_name, options)
        await connector.disconnect()

        if not result.success:
            return {"success": False, "error": result.error}

        twin_result: dict[str, Any] = {}
        if persist and result.data:
            twin_result = await self.twin_service.process_import(
                tenant_id=connector_record.tenant_id,
                raw_data=result.data,
                entity_type=entity_type,
                source_system=connector_record.connector_type,
                connector_id=connector_record.id,
                sync_job_id=sync_job_id,
                user_id=user_id,
                ingest_knowledge=True,
            )
            result.data["twin"] = twin_result

            if entity_type == ImportEntityType.LEDGERS:
                count = await self._persist_ledgers(connector_record.tenant_id, result.data.get("ledgers", []))
                result.data["persisted"] = count
            elif entity_type in (ImportEntityType.STOCK_ITEMS, ImportEntityType.INVENTORY):
                count = await self._persist_items(connector_record.tenant_id, result.data.get("items", []))
                result.data["persisted"] = count
            elif entity_type == ImportEntityType.VENDORS:
                count = await self._persist_vendors(connector_record.tenant_id, result.data.get("ledgers", []))
                result.data["persisted"] = count
            elif entity_type == ImportEntityType.CUSTOMERS:
                count = await self._persist_customers(connector_record.tenant_id, result.data.get("ledgers", []))
                result.data["persisted"] = count

        return {"success": True, "data": result.data, "warnings": result.warnings, "twin": twin_result}

    async def _persist_ledgers(self, tenant_id: UUID, ledgers: list[dict[str, Any]]) -> int:
        count = 0
        for ledger_data in ledgers:
            existing = await self.db.execute(
                select(Ledger).where(
                    Ledger.tenant_id == tenant_id,
                    Ledger.name == ledger_data["name"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            ledger = Ledger(
                tenant_id=tenant_id,
                name=ledger_data["name"],
                parent_group=ledger_data.get("parent_group"),
                ledger_type=ledger_data.get("ledger_type", "general"),
                opening_balance=Decimal(str(ledger_data.get("opening_balance", 0))),
                gstin=ledger_data.get("gstin"),
                pan=ledger_data.get("pan"),
                address=ledger_data.get("address"),
                tally_ledger_name=ledger_data["name"],
            )
            self.db.add(ledger)
            count += 1
        await self.db.flush()
        return count

    async def _persist_items(self, tenant_id: UUID, items: list[dict[str, Any]]) -> int:
        count = 0
        for item_data in items:
            existing = await self.db.execute(
                select(Item).where(Item.tenant_id == tenant_id, Item.name == item_data["name"])
            )
            if existing.scalar_one_or_none():
                continue
            item = Item(
                tenant_id=tenant_id,
                name=item_data["name"],
                unit=item_data.get("unit", "NOS"),
                hsn_code=item_data.get("hsn_code"),
                gst_rate=Decimal(str(item_data["gst_rate"])) if item_data.get("gst_rate") else None,
                default_rate=Decimal(str(item_data["rate"])) if item_data.get("rate") else None,
                category=item_data.get("category"),
                tally_stock_item_name=item_data["name"],
            )
            self.db.add(item)
            count += 1
        await self.db.flush()
        return count

    async def _persist_vendors(self, tenant_id: UUID, ledgers: list[dict[str, Any]]) -> int:
        count = 0
        for ledger_data in ledgers:
            if ledger_data.get("ledger_type") not in ("vendor", "general"):
                continue
            existing = await self.db.execute(
                select(Vendor).where(Vendor.tenant_id == tenant_id, Vendor.name == ledger_data["name"])
            )
            if existing.scalar_one_or_none():
                continue
            vendor = Vendor(
                tenant_id=tenant_id,
                name=ledger_data["name"],
                gstin=ledger_data.get("gstin"),
                pan=ledger_data.get("pan"),
                address=ledger_data.get("address"),
            )
            self.db.add(vendor)
            count += 1
        await self.db.flush()
        return count

    async def _persist_customers(self, tenant_id: UUID, ledgers: list[dict[str, Any]]) -> int:
        count = 0
        for ledger_data in ledgers:
            if ledger_data.get("ledger_type") not in ("customer", "general"):
                continue
            existing = await self.db.execute(
                select(Customer).where(Customer.tenant_id == tenant_id, Customer.name == ledger_data["name"])
            )
            if existing.scalar_one_or_none():
                continue
            customer = Customer(
                tenant_id=tenant_id,
                name=ledger_data["name"],
                gstin=ledger_data.get("gstin"),
                pan=ledger_data.get("pan"),
                address=ledger_data.get("address"),
            )
            self.db.add(customer)
            count += 1
        await self.db.flush()
        return count
