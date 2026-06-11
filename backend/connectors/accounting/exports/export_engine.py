from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.base.types import ExportEntityType, VoucherExportFormat
from backend.connectors.accounting.validation.validator import AccountingValidator
from backend.models.accounting import AccountingConnector, VoucherExport


class ExportEngine:
    """Export vouchers and reports to accounting systems — requires prior validation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_voucher(
        self,
        connector_record: AccountingConnector,
        voucher_data: dict[str, Any],
        voucher_draft_id: UUID,
        company_id: UUID | None,
        user_id: UUID,
        skip_validation: bool = False,
    ) -> dict[str, Any]:
        if not skip_validation:
            validation = AccountingValidator.validate_voucher_draft(voucher_data)
            if not validation.is_valid:
                return {
                    "success": False,
                    "error": "Voucher validation failed",
                    "validation": AccountingValidator.to_dict(validation),
                }

        connector = accounting_connector_registry.create_instance(
            connector_record.connector_type,
            connector_record.config,
        )
        await connector.connect()
        result = await connector.export_voucher(
            voucher_data,
            company_name=connector_record.config.get("company_name"),
            export_format=VoucherExportFormat.TALLY_XML,
        )
        await connector.disconnect()

        export_record = VoucherExport(
            tenant_id=connector_record.tenant_id,
            voucher_draft_id=voucher_draft_id,
            connector_id=connector_record.id,
            company_id=company_id,
            status="exported" if result.success else "failed",
            export_format="tally_xml",
            export_payload=result.data,
            file_path=result.data.get("file_path"),
            exported_at=datetime.now(timezone.utc) if result.success else None,
            exported_by=user_id,
            error_message=result.error,
        )
        self.db.add(export_record)
        await self.db.flush()

        return {
            "success": result.success,
            "export_id": str(export_record.id),
            "data": result.data,
            "error": result.error,
            "warnings": result.warnings,
        }

    async def export_report(
        self,
        connector_record: AccountingConnector,
        entity_type: ExportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connector = accounting_connector_registry.create_instance(
            connector_record.connector_type,
            connector_record.config,
        )
        await connector.connect()
        result = await connector.export_entities(entity_type, company_name, options)
        await connector.disconnect()
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }
