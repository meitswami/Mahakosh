from datetime import date
from typing import Any

import httpx

from backend.connectors.accounting.base.types import ExportEntityType, ImportEntityType
from backend.connectors.accounting.xml.generator import TallyXMLGenerator
from backend.connectors.accounting.xml.parser import TallyXMLParser


class TallyXMLEngine:
    """HTTP XML transport engine for Tally Prime / ERP 9 / Silver / Gold."""

    def __init__(self, host: str = "localhost", port: int = 9000, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

    async def send_request(self, xml_payload: str) -> tuple[bool, str, str | None]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    content=xml_payload.encode("utf-8"),
                    headers={"Content-Type": "application/xml"},
                )
                if response.status_code >= 400:
                    return False, "", f"HTTP {response.status_code}: {response.text[:300]}"
                return True, response.text, None
        except httpx.ConnectError:
            return False, "", f"Cannot connect to Tally at {self.base_url}. Ensure Tally is running with ODBC/XML server enabled."
        except httpx.TimeoutException:
            return False, "", f"Tally request timed out after {self.timeout}s"
        except Exception as exc:
            return False, "", str(exc)

    async def health_check(self) -> dict[str, Any]:
        ok, response, error = await self.send_request(TallyXMLGenerator.list_companies())
        if not ok:
            return {"healthy": False, "error": error}
        parsed = TallyXMLParser.parse_response(response)
        return {
            "healthy": parsed.get("success", False),
            "tally_version": TallyXMLParser.extract_tally_version(response),
            "endpoint": self.base_url,
        }

    async def discover_companies(self) -> tuple[bool, list, str | None]:
        ok, response, error = await self.send_request(TallyXMLGenerator.list_companies())
        if not ok:
            return False, [], error
        return True, TallyXMLParser.parse_companies(response), None

    async def import_ledgers(self, company_name: str | None = None) -> tuple[bool, list, str | None]:
        ok, response, error = await self.send_request(TallyXMLGenerator.list_ledgers(company_name))
        if not ok:
            return False, [], error
        return True, TallyXMLParser.parse_ledgers(response), None

    async def import_stock_items(self, company_name: str | None = None) -> tuple[bool, list, str | None]:
        ok, response, error = await self.send_request(TallyXMLGenerator.list_stock_items(company_name))
        if not ok:
            return False, [], error
        return True, TallyXMLParser.parse_stock_items(response), None

    async def import_vouchers(
        self,
        company_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> tuple[bool, list, str | None]:
        ok, response, error = await self.send_request(
            TallyXMLGenerator.list_vouchers(company_name, from_date, to_date)
        )
        if not ok:
            return False, [], error
        return True, TallyXMLParser.parse_vouchers(response), None

    async def export_voucher(self, voucher: dict[str, Any]) -> tuple[bool, str, str | None]:
        xml_payload = TallyXMLGenerator.voucher_xml(voucher)
        ok, response, error = await self.send_request(xml_payload)
        if not ok:
            return False, xml_payload, error
        parsed = TallyXMLParser.parse_response(response)
        if not parsed.get("success"):
            return False, xml_payload, parsed.get("error", "Tally rejected voucher import")
        return True, xml_payload, None

    async def export_report(
        self,
        entity_type: ExportEntityType,
        company_name: str | None = None,
    ) -> tuple[bool, str, str | None]:
        generators = {
            ExportEntityType.TRIAL_BALANCE: TallyXMLGenerator.trial_balance,
            ExportEntityType.PROFIT_LOSS: TallyXMLGenerator.profit_and_loss,
            ExportEntityType.BALANCE_SHEET: TallyXMLGenerator.balance_sheet,
            ExportEntityType.GST_DATA: TallyXMLGenerator.gst_report,
            ExportEntityType.STOCK_SUMMARY: TallyXMLGenerator.stock_summary,
            ExportEntityType.LEDGERS: TallyXMLGenerator.list_ledgers,
        }
        gen = generators.get(entity_type)
        if not gen:
            return False, "", f"Export type {entity_type.value} not supported via XML"
        ok, response, error = await self.send_request(gen(company_name))
        return ok, response, error

    def generate_voucher_xml(self, voucher: dict[str, Any]) -> str:
        return TallyXMLGenerator.voucher_xml(voucher)

    def parse_file(self, file_path: str, entity_type: ImportEntityType) -> list:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        parsers = {
            ImportEntityType.LEDGERS: TallyXMLParser.parse_ledgers,
            ImportEntityType.STOCK_ITEMS: TallyXMLParser.parse_stock_items,
            ImportEntityType.VOUCHERS: TallyXMLParser.parse_vouchers,
            ImportEntityType.GROUPS: TallyXMLParser.parse_groups,
        }
        parser = parsers.get(entity_type)
        if not parser:
            return []
        return parser(content)
