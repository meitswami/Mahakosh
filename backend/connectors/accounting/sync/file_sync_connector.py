import os
from pathlib import Path
from typing import Any

from backend.connectors.accounting.base.connector import BaseAccountingConnector
from backend.connectors.accounting.base.registry import accounting_connector_registry
from backend.connectors.accounting.base.types import (
    AccountingConnectorType,
    ConnectorOperationResult,
    ConnectorStatus,
    ExportEntityType,
    ImportEntityType,
    VoucherExportFormat,
)
from backend.connectors.accounting.xml.engine import TallyXMLEngine
from backend.connectors.accounting.xml.generator import TallyXMLGenerator


class FileSyncConnector(BaseAccountingConnector):
    """Priority-3 connector — file-based XML import/export folder sync."""

    connector_type = AccountingConnectorType.FILE_SYNC
    name = "file_sync"
    description = "File-based Tally XML sync via import/export folders"
    version = "1.0.0"
    priority = 3
    supported_erp_systems = ["Tally Prime", "Tally ERP 9", "File-based ERP"]

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.import_folder = Path(config.get("import_folder", "./tally/import"))
        self.export_folder = Path(config.get("export_folder", "./tally/export"))
        self.xml_folder = Path(config.get("xml_folder", "./tally/xml"))
        self._engine = TallyXMLEngine()

    async def connect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.CONNECTING
        for folder in (self.import_folder, self.export_folder, self.xml_folder):
            folder.mkdir(parents=True, exist_ok=True)
        self.status = ConnectorStatus.CONNECTED
        return ConnectorOperationResult(
            success=True,
            data={
                "import_folder": str(self.import_folder),
                "export_folder": str(self.export_folder),
                "xml_folder": str(self.xml_folder),
            },
        )

    async def disconnect(self) -> ConnectorOperationResult:
        self.status = ConnectorStatus.DISCONNECTED
        return ConnectorOperationResult(success=True)

    async def health_check(self) -> ConnectorOperationResult:
        folders = {
            "import": self.import_folder.exists(),
            "export": self.export_folder.exists(),
            "xml": self.xml_folder.exists(),
        }
        healthy = all(folders.values())
        return ConnectorOperationResult(
            success=healthy,
            data={"folders": folders, "writable": os.access(self.export_folder, os.W_OK)},
        )

    async def discover_companies(self) -> ConnectorOperationResult:
        companies = []
        for xml_file in self.xml_folder.glob("*.xml"):
            data = self._engine.parse_file(str(xml_file), ImportEntityType.LEDGERS)
            if data:
                companies.append({"name": xml_file.stem, "source_file": xml_file.name})
        return ConnectorOperationResult(success=True, data={"companies": companies, "count": len(companies)})

    async def import_entities(
        self,
        entity_type: ImportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        folder = self.import_folder
        all_data = []
        for xml_file in folder.glob("*.xml"):
            records = self._engine.parse_file(str(xml_file), entity_type)
            all_data.extend(records)

        if entity_type == ImportEntityType.LEDGERS:
            return ConnectorOperationResult(
                success=True,
                data={"ledgers": self.ledgers_to_dict(all_data), "count": len(all_data), "source": "file"},
            )
        if entity_type in (ImportEntityType.STOCK_ITEMS, ImportEntityType.INVENTORY):
            return ConnectorOperationResult(
                success=True,
                data={"items": self.items_to_dict(all_data), "count": len(all_data), "source": "file"},
            )
        if entity_type == ImportEntityType.VOUCHERS:
            return ConnectorOperationResult(
                success=True,
                data={"vouchers": all_data, "count": len(all_data), "source": "file"},
            )
        return ConnectorOperationResult(success=True, data={"records": all_data, "count": len(all_data)})

    async def export_entities(
        self,
        entity_type: ExportEntityType,
        company_name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> ConnectorOperationResult:
        return ConnectorOperationResult(
            success=False,
            error="Use export_voucher for file-based voucher export",
        )

    async def export_voucher(
        self,
        voucher_data: dict[str, Any],
        company_name: str | None = None,
        export_format: VoucherExportFormat = VoucherExportFormat.TALLY_XML,
    ) -> ConnectorOperationResult:
        xml_payload = TallyXMLGenerator.voucher_xml(voucher_data)
        vch_num = voucher_data.get("voucher_number", "draft")
        file_name = f"voucher_{vch_num}_{voucher_data.get('voucher_type', 'purchase')}.xml"
        file_path = self.export_folder / file_name
        file_path.write_text(xml_payload, encoding="utf-8")
        return ConnectorOperationResult(
            success=True,
            data={"xml": xml_payload, "file_path": str(file_path), "format": "tally_xml"},
        )


accounting_connector_registry.register(FileSyncConnector)
