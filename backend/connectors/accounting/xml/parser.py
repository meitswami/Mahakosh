import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.connectors.accounting.base.types import CompanyInfo, LedgerInfo, StockItemInfo


class TallyXMLParser:
    """Parse Tally XML responses into structured data."""

    @staticmethod
    def _text(elem: ET.Element | None, default: str = "") -> str:
        if elem is None or elem.text is None:
            return default
        return elem.text.strip()

    @staticmethod
    def _decimal(value: str | None, default: Decimal = Decimal("0")) -> Decimal:
        if not value:
            return default
        cleaned = value.replace(",", "").strip()
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return default

    @classmethod
    def parse_response(cls, xml_text: str) -> dict[str, Any]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            return {"success": False, "error": str(exc), "raw": xml_text[:500]}

        status = root.find(".//STATUS")
        if status is not None and status.text and int(status.text) == 0:
            line_error = root.find(".//LINEERROR")
            return {
                "success": False,
                "error": cls._text(line_error, "Tally returned error status"),
            }

        return {"success": True, "root": root, "raw": xml_text}

    @classmethod
    def parse_companies(cls, xml_text: str) -> list[CompanyInfo]:
        parsed = cls.parse_response(xml_text)
        if not parsed.get("success"):
            return []

        companies: list[CompanyInfo] = []
        root = parsed["root"]
        for company_el in root.findall(".//COMPANY") + root.findall(".//COLLECTION/COMPANY"):
            name = company_el.get("NAME") or cls._text(company_el.find("NAME"))
            if not name:
                continue
            fy = cls._text(company_el.find("CURRENTFINPERIOD"))
            books_from = None
            books_from_text = cls._text(company_el.find("BOOKSFROM"))
            if books_from_text and len(books_from_text) >= 8:
                try:
                    books_from = datetime.strptime(books_from_text[:8], "%Y%m%d").date()
                except ValueError:
                    pass
            companies.append(
                CompanyInfo(
                    name=name,
                    financial_year=fy or None,
                    books_begin_from=books_from,
                    books_status=cls._text(company_el.find("BOOKSSTATUS")) or None,
                    metadata={"source": "tally_xml"},
                )
            )
        return companies

    @classmethod
    def parse_ledgers(cls, xml_text: str) -> list[LedgerInfo]:
        parsed = cls.parse_response(xml_text)
        if not parsed.get("success"):
            return []

        ledgers: list[LedgerInfo] = []
        root = parsed["root"]
        for ledger_el in root.findall(".//LEDGER"):
            name = ledger_el.get("NAME") or cls._text(ledger_el.find("NAME"))
            if not name:
                continue
            gstin = cls._text(ledger_el.find(".//GSTIN")) or None
            ledgers.append(
                LedgerInfo(
                    name=name,
                    parent_group=cls._text(ledger_el.find("PARENT")) or None,
                    ledger_type=cls._classify_ledger(name, cls._text(ledger_el.find("PARENT"))),
                    opening_balance=cls._decimal(cls._text(ledger_el.find("OPENINGBALANCE"))),
                    gstin=gstin if gstin else None,
                    pan=cls._text(ledger_el.find("INCOMETAXNUMBER")) or None,
                    address=cls._text(ledger_el.find("ADDRESS")) or None,
                    metadata={"source": "tally_xml"},
                )
            )
        return ledgers

    @classmethod
    def parse_stock_items(cls, xml_text: str) -> list[StockItemInfo]:
        parsed = cls.parse_response(xml_text)
        if not parsed.get("success"):
            return []

        items: list[StockItemInfo] = []
        root = parsed["root"]
        for item_el in root.findall(".//STOCKITEM"):
            name = item_el.get("NAME") or cls._text(item_el.find("NAME"))
            if not name:
                continue
            gst_rate_text = cls._text(item_el.find("GSTRATE"))
            gst_rate = cls._decimal(gst_rate_text) if gst_rate_text else None
            items.append(
                StockItemInfo(
                    name=name,
                    unit=cls._text(item_el.find("BASEUNITS"), "NOS"),
                    hsn_code=cls._text(item_el.find("HSNCODE")) or None,
                    gst_rate=gst_rate,
                    opening_stock=cls._decimal(cls._text(item_el.find("OPENINGBALANCE"))),
                    rate=cls._decimal(cls._text(item_el.find("STANDARDPRICE"))) or None,
                    category=cls._text(item_el.find("CATEGORY")) or None,
                    metadata={"source": "tally_xml"},
                )
            )
        return items

    @classmethod
    def parse_vouchers(cls, xml_text: str) -> list[dict[str, Any]]:
        parsed = cls.parse_response(xml_text)
        if not parsed.get("success"):
            return []

        vouchers: list[dict[str, Any]] = []
        root = parsed["root"]
        for vch_el in root.findall(".//VOUCHER"):
            vch_type = vch_el.get("VCHTYPE", "Journal")
            date_text = cls._text(vch_el.find("DATE"))
            vch_date = None
            if date_text and len(date_text) >= 8:
                try:
                    vch_date = datetime.strptime(date_text[:8], "%Y%m%d").date().isoformat()
                except ValueError:
                    vch_date = date_text

            lines = []
            for entry in vch_el.findall("ALLLEDGERENTRIES.LIST"):
                lines.append({
                    "ledger": cls._text(entry.find("LEDGERNAME")),
                    "amount": float(cls._decimal(cls._text(entry.find("AMOUNT")))),
                    "is_debit": cls._text(entry.find("ISDEEMEDPOSITIVE")).lower() == "yes",
                })

            vouchers.append({
                "voucher_type": vch_type,
                "voucher_number": cls._text(vch_el.find("VOUCHERNUMBER")) or None,
                "voucher_date": vch_date,
                "party_name": cls._text(vch_el.find("PARTYLEDGERNAME")) or None,
                "narration": cls._text(vch_el.find("NARRATION")) or None,
                "lines": lines,
                "total_amount": sum(abs(l["amount"]) for l in lines) / 2 if lines else 0,
            })
        return vouchers

    @classmethod
    def parse_groups(cls, xml_text: str) -> list[dict[str, Any]]:
        parsed = cls.parse_response(xml_text)
        if not parsed.get("success"):
            return []
        groups = []
        for group_el in parsed["root"].findall(".//GROUP"):
            name = group_el.get("NAME") or cls._text(group_el.find("NAME"))
            if name:
                groups.append({
                    "name": name,
                    "parent": cls._text(group_el.find("PARENT")) or None,
                })
        return groups

    @staticmethod
    def _classify_ledger(name: str, parent: str) -> str:
        name_lower = name.lower()
        parent_lower = (parent or "").lower()
        if "sundry debtor" in parent_lower or "debtor" in parent_lower:
            return "customer"
        if "sundry creditor" in parent_lower or "creditor" in parent_lower:
            return "vendor"
        if "bank" in parent_lower or "bank" in name_lower:
            return "bank"
        if "cash" in parent_lower:
            return "cash"
        if "duties" in parent_lower or "tax" in name_lower or "gst" in name_lower:
            return "tax"
        if "sales" in parent_lower:
            return "sales"
        if "purchase" in parent_lower:
            return "purchase"
        return "general"

    @staticmethod
    def extract_tally_version(xml_text: str) -> str | None:
        match = re.search(r"Tally\s*(?:Prime|ERP\s*9)?\s*[\d.]+", xml_text, re.IGNORECASE)
        return match.group(0) if match else None
