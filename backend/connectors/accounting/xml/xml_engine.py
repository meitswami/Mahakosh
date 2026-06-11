"""Tally XML generation and parsing engine."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from typing import Any


def _text_el(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def _amount(value: Any) -> str:
    if value is None:
        return "0.00"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return f"{float(value):.2f}"


class TallyXMLEngine:
    """Generate and parse Tally-compatible XML envelopes."""

    @staticmethod
    def envelope_header(version: str = "1", tally_request: str = "Import Data") -> ET.Element:
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        _text_el(header, "VERSION", version)
        _text_el(header, "TALLYREQUEST", tally_request)
        return envelope

    @classmethod
    def export_request(cls, report_name: str, company: str) -> str:
        envelope = cls.envelope_header(tally_request="Export Data")
        body = ET.SubElement(envelope, "BODY")
        export_data = ET.SubElement(body, "EXPORTDATA")
        req_desc = ET.SubElement(export_data, "REQUESTDESC")
        _text_el(req_desc, "REPORTNAME", report_name)
        _text_el(req_desc, "STATICVARIABLES")
        static = req_desc.find("STATICVARIABLES")
        if static is not None:
            _text_el(static, "SVCURRENTCOMPANY", company)
        return ET.tostring(envelope, encoding="unicode")

    @classmethod
    def company_list_request(cls) -> str:
        envelope = cls.envelope_header(tally_request="Export Data")
        body = ET.SubElement(envelope, "BODY")
        export_data = ET.SubElement(body, "EXPORTDATA")
        req_desc = ET.SubElement(export_data, "REQUESTDESC")
        _text_el(req_desc, "REPORTNAME", "List of Companies")
        return ET.tostring(envelope, encoding="unicode")

    @classmethod
    def ledger_master(cls, name: str, parent: str, opening_balance: float = 0, gstin: str | None = None) -> str:
        envelope = cls.envelope_header()
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        req_desc = ET.SubElement(import_data, "REQUESTDESC")
        _text_el(req_desc, "REPORTNAME", "All Masters")
        _text_el(req_desc, "STATICVARIABLES")
        static = req_desc.find("STATICVARIABLES")
        if static is not None:
            _text_el(static, "IMPORTDUPS", "Ignore Duplicates")
        req_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        ledger = ET.SubElement(tally_msg, "LEDGER", {"NAME": name, "ACTION": "Create"})
        _text_el(ledger, "NAME", name)
        _text_el(ledger, "PARENT", parent)
        _text_el(ledger, "OPENINGBALANCE", _amount(opening_balance))
        if gstin:
            _text_el(ledger, "PARTYGSTIN", gstin)
        return ET.tostring(envelope, encoding="unicode")

    @classmethod
    def stock_item(
        cls,
        name: str,
        parent: str = "Primary",
        unit: str = "Nos",
        gst_rate: float | None = None,
        hsn: str | None = None,
    ) -> str:
        envelope = cls.envelope_header()
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        req_desc = ET.SubElement(import_data, "REQUESTDESC")
        _text_el(req_desc, "REPORTNAME", "All Masters")
        req_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        stock = ET.SubElement(tally_msg, "STOCKITEM", {"NAME": name, "ACTION": "Create"})
        _text_el(stock, "NAME", name)
        _text_el(stock, "PARENT", parent)
        _text_el(stock, "BASEUNITS", unit)
        if hsn:
            _text_el(stock, "HSNCODE", hsn)
        if gst_rate is not None:
            gst_details = ET.SubElement(stock, "GSTDETAILS.LIST")
            _text_el(gst_details, "TAXABILITY", "Taxable")
            state_details = ET.SubElement(gst_details, "STATEWISEDETAILS.LIST")
            rate_details = ET.SubElement(state_details, "RATEDETAILS.LIST")
            _text_el(rate_details, "GSTRATEDUTYHEAD", "Central Tax")
            _text_el(rate_details, "GSTRATE", str(gst_rate / 2))
        return ET.tostring(envelope, encoding="unicode")

    @classmethod
    def voucher(cls, voucher_data: dict[str, Any]) -> str:
        vch_type = voucher_data.get("voucher_type", "Purchase")
        vch_date = voucher_data.get("voucher_date", date.today().isoformat())
        party = voucher_data.get("party_name", voucher_data.get("party", ""))
        narration = voucher_data.get("narration", "")
        lines = voucher_data.get("lines", [])

        envelope = cls.envelope_header()
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        req_desc = ET.SubElement(import_data, "REQUESTDESC")
        _text_el(req_desc, "REPORTNAME", "Vouchers")
        req_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        voucher_el = ET.SubElement(
            tally_msg,
            "VOUCHER",
            {
                "VCHTYPE": vch_type.title(),
                "ACTION": "Create",
                "OBJVIEW": "Accounting Voucher View",
            },
        )
        _text_el(voucher_el, "DATE", vch_date.replace("-", ""))
        _text_el(voucher_el, "VOUCHERTYPENAME", vch_type.title())
        _text_el(voucher_el, "NARRATION", narration)
        if party:
            _text_el(voucher_el, "PARTYLEDGERNAME", party)

        for line in lines:
            entry = ET.SubElement(voucher_el, "ALLLEDGERENTRIES.LIST")
            ledger_name = line.get("ledger") or line.get("description", "Suspense")
            _text_el(entry, "LEDGERNAME", ledger_name)
            debit = float(line.get("debit", 0) or 0)
            credit = float(line.get("credit", 0) or 0)
            if debit > 0:
                _text_el(entry, "ISDEEMEDPOSITIVE", "Yes")
                _text_el(entry, "AMOUNT", f"-{_amount(debit)}")
            elif credit > 0:
                _text_el(entry, "ISDEEMEDPOSITIVE", "No")
                _text_el(entry, "AMOUNT", _amount(credit))

            if line.get("quantity"):
                inv = ET.SubElement(entry, "INVENTORYENTRIES.LIST")
                _text_el(inv, "STOCKITEMNAME", line.get("item_name", line.get("description", "")))
                _text_el(inv, "ACTUALQTY", f"{line['quantity']} {line.get('unit', 'Nos')}")
                _text_el(inv, "RATE", _amount(line.get("rate", 0)))
                _text_el(inv, "AMOUNT", _amount(line.get("amount", 0)))

        return ET.tostring(envelope, encoding="unicode")

    @classmethod
    def company_info_request(cls, company: str) -> str:
        envelope = cls.envelope_header(tally_request="Export Data")
        body = ET.SubElement(envelope, "BODY")
        export_data = ET.SubElement(body, "EXPORTDATA")
        req_desc = ET.SubElement(export_data, "REQUESTDESC")
        _text_el(req_desc, "REPORTNAME", "Company Info")
        _text_el(req_desc, "STATICVARIABLES")
        static = req_desc.find("STATICVARIABLES")
        if static is not None:
            _text_el(static, "SVCURRENTCOMPANY", company)
        return ET.tostring(envelope, encoding="unicode")

    @staticmethod
    def parse_response(xml_text: str) -> dict[str, Any]:
        root = ET.fromstring(xml_text)
        result: dict[str, Any] = {"companies": [], "ledgers": [], "stock_items": [], "vouchers": []}

        for company in root.iter("COMPANY"):
            name = company.findtext("NAME") or company.get("NAME")
            if name:
                result["companies"].append({
                    "name": name,
                    "financial_year": company.findtext("CURRENTFY") or company.findtext("STARTINGFROM"),
                    "books_status": company.findtext("BOOKSFROM"),
                })

        for ledger in root.iter("LEDGER"):
            name = ledger.get("NAME") or ledger.findtext("NAME")
            if name:
                result["ledgers"].append({
                    "name": name,
                    "parent": ledger.findtext("PARENT"),
                    "opening_balance": ledger.findtext("OPENINGBALANCE", "0"),
                    "gstin": ledger.findtext("PARTYGSTIN"),
                })

        for item in root.iter("STOCKITEM"):
            name = item.get("NAME") or item.findtext("NAME")
            if name:
                result["stock_items"].append({
                    "name": name,
                    "parent": item.findtext("PARENT"),
                    "unit": item.findtext("BASEUNITS"),
                    "hsn": item.findtext("HSNCODE"),
                })

        for vch in root.iter("VOUCHER"):
            result["vouchers"].append({
                "voucher_type": vch.findtext("VOUCHERTYPENAME") or vch.get("VCHTYPE"),
                "date": vch.findtext("DATE"),
                "party": vch.findtext("PARTYLEDGERNAME"),
                "amount": vch.findtext("AMOUNT"),
            })

        return result
