"""File sync connector — priority 3, folder-based import/export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.connectors.accounting.base.base_accounting_connector import (
    AccountingConnectorConfig,
    AccountingConnectorResult,
    AccountingConnectorStatus,
    AccountingConnectorType,
    BaseAccountingConnector,
)
from backend.connectors.accounting.exports.export_engine import ExportEngine
from backend.connectors.accounting.imports.import_engine import ImportEngine
from backend.connectors.accounting.sync.file_watcher import TallyFileWatcher


class FileSyncConnector(BaseAccountingConnector):
    name = "file_sync"
    connector_type = AccountingConnectorType.FILE_SYNC
    description = "Folder-based accounting file sync (XML/CSV)"
    version = "1.0.0"
    priority = 3

    def __init__(self, config: AccountingConnectorConfig):
        super().__init__(config)
        self._import_engine = ImportEngine()
        self._export_engine = ExportEngine()
        self._watcher: TallyFileWatcher | None = None

    def _folders(self) -> dict[str, Path]:
        base = Path(self.config.options.get("base_folder", "./tally_data"))
        return {
            "import": Path(self.config.options.get("import_folder", base / "import")),
            "export": Path(self.config.options.get("export_folder", base / "export")),
            "xml": Path(self.config.options.get("xml_folder", base / "xml")),
        }

    async def connect(self) -> AccountingConnectorResult:
        folders = self._folders()
        for folder in folders.values():
            folder.mkdir(parents=True, exist_ok=True)
        self.status = AccountingConnectorStatus.CONNECTED
        return AccountingConnectorResult(
            success=True,
            data={"folders": {k: str(v) for k, v in folders.items()}},
            source="file_sync",
        )

    async def disconnect(self) -> AccountingConnectorResult:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self.status = AccountingConnectorStatus.DISCONNECTED
        return AccountingConnectorResult(success=True, data={"disconnected": True})

    async def health_check(self) -> AccountingConnectorResult:
        folders = self._folders()
        accessible = all(f.exists() for f in folders.values())
        return AccountingConnectorResult(success=accessible, data={"folders_ok": accessible})

    async def discover_companies(self) -> AccountingConnectorResult:
        company = self.config.company_name or "Default"
        return AccountingConnectorResult(
            success=True,
            data={"companies": [{"name": company, "source": "file_sync"}]},
        )

    async def import_masters(self, entity_types: list[str], company_name: str | None = None) -> AccountingConnectorResult:
        folders = self._folders()
        results: dict[str, Any] = {}
        for entity_type in entity_types:
            key = "ledgers" if entity_type in ("ledgers", "groups") else "stock_items"
            collected = []
            for folder in (folders["import"], folders["xml"]):
                for file_path in folder.glob("*.xml"):
                    collected.extend(self._import_engine.import_from_file(str(file_path), entity_type))
            results[key] = collected
        return AccountingConnectorResult(success=True, data=results, source="file_sync")

    async def import_transactions(self, entity_types: list[str], company_name: str | None = None, from_date: str | None = None) -> AccountingConnectorResult:
        folders = self._folders()
        results: dict[str, Any] = {}
        if "vouchers" in entity_types:
            vouchers = []
            for folder in (folders["import"], folders["xml"]):
                for file_path in folder.glob("*.xml"):
                    vouchers.extend(self._import_engine.import_from_file(str(file_path), "vouchers"))
            results["vouchers"] = vouchers
        return AccountingConnectorResult(success=True, data=results, source="file_sync")

    async def export_report(self, report_type: str, company_name: str | None = None) -> AccountingConnectorResult:
        result = self._export_engine.generate_report(report_type, company_name or self.config.company_name or "Default")
        folders = self._folders()
        export_path = folders["export"] / f"{report_type}.json"
        import json
        export_path.write_text(json.dumps(result.data, indent=2), encoding="utf-8")
        result.data["file_path"] = str(export_path)
        return result

    async def export_voucher(self, voucher_data: dict[str, Any], company_name: str | None = None) -> AccountingConnectorResult:
        xml = self._export_engine.export_voucher_xml(voucher_data)
        folders = self._folders()
        vch_num = voucher_data.get("voucher_number", "draft")
        file_path = folders["export"] / f"voucher_{vch_num}.xml"
        file_path.write_text(xml, encoding="utf-8")
        return AccountingConnectorResult(
            success=True,
            data={"xml": xml, "file_path": str(file_path)},
            source="file_sync",
        )
