import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from typing import Any


class TallyXMLGenerator:
    """Generate Tally-compatible XML envelopes for import/export operations."""

    @staticmethod
    def _envelope(request_type: str, collection_id: str, body_elements: list[ET.Element] | None = None) -> str:
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        ET.SubElement(header, "VERSION").text = "1"
        ET.SubElement(header, "TALLYREQUEST").text = request_type
        ET.SubElement(header, "TYPE").text = "Data" if request_type == "Import" else "Collection"
        ET.SubElement(header, "ID").text = collection_id

        body = ET.SubElement(envelope, "BODY")
        desc = ET.SubElement(body, "DESC")
        static_vars = ET.SubElement(desc, "STATICVARIABLES")
        ET.SubElement(static_vars, "SVEXPORTFORMAT").text = "$$SysName:XML"

        if body_elements:
            data = ET.SubElement(body, "DATA")
            tally_msg = ET.SubElement(data, "TALLYMESSAGE")
            for elem in body_elements:
                tally_msg.append(elem)

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(envelope, encoding="unicode")

    @classmethod
    def list_companies(cls) -> str:
        return cls._envelope("Export", "List of Companies")

    @classmethod
    def list_ledgers(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "List of Ledgers")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def list_stock_items(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "List of Stock Items")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def list_vouchers(cls, company_name: str | None = None, from_date: date | None = None, to_date: date | None = None) -> str:
        xml = cls._envelope("Export", "Voucher Register")
        root = ET.fromstring(xml)
        sv = root.find(".//STATICVARIABLES")
        if sv is not None:
            if company_name:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            if from_date:
                ET.SubElement(sv, "SVFROMDATE").text = from_date.strftime("%Y%m%d")
            if to_date:
                ET.SubElement(sv, "SVTODATE").text = to_date.strftime("%Y%m%d")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")

    @classmethod
    def trial_balance(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "Trial Balance")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def profit_and_loss(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "Profit and Loss")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def balance_sheet(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "Balance Sheet")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def gst_report(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "GST Report")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def stock_summary(cls, company_name: str | None = None) -> str:
        xml = cls._envelope("Export", "Stock Summary")
        if company_name:
            root = ET.fromstring(xml)
            sv = root.find(".//STATICVARIABLES")
            if sv is not None:
                ET.SubElement(sv, "SVCURRENTCOMPANY").text = company_name
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
        return xml

    @classmethod
    def ledger_master(cls, ledger_data: dict[str, Any]) -> str:
        ledger = ET.Element("LEDGER", NAME=ledger_data.get("name", ""))
        if ledger_data.get("parent_group"):
            ET.SubElement(ledger, "PARENT").text = ledger_data["parent_group"]
        if ledger_data.get("opening_balance") is not None:
            ET.SubElement(ledger, "OPENINGBALANCE").text = str(ledger_data["opening_balance"])
        if ledger_data.get("gstin"):
            party = ET.SubElement(ledger, "LEDGERGSTREGDETAILS.LIST")
            ET.SubElement(party, "GSTIN").text = ledger_data["gstin"]
        return cls._envelope("Import", "All Masters", [ledger])

    @classmethod
    def stock_item_master(cls, item_data: dict[str, Any]) -> str:
        item = ET.Element("STOCKITEM", NAME=item_data.get("name", ""))
        if item_data.get("unit"):
            ET.SubElement(item, "BASEUNITS").text = item_data["unit"]
        if item_data.get("hsn_code"):
            ET.SubElement(item, "HSNCODE").text = item_data["hsn_code"]
        if item_data.get("gst_rate") is not None:
            ET.SubElement(item, "GSTRATE").text = str(item_data["gst_rate"])
        if item_data.get("rate") is not None:
            ET.SubElement(item, "STANDARDPRICE").text = str(item_data["rate"])
        return cls._envelope("Import", "All Masters", [item])

    @classmethod
    def voucher_xml(cls, voucher: dict[str, Any]) -> str:
        vch_type = voucher.get("voucher_type", "Purchase")
        vch_date = voucher.get("voucher_date", date.today())
        if isinstance(vch_date, str):
            vch_date_str = vch_date.replace("-", "")
        else:
            vch_date_str = vch_date.strftime("%Y%m%d")

        voucher_el = ET.Element(
            "VOUCHER",
            VCHTYPE=vch_type,
            ACTION="Create",
        )
        ET.SubElement(voucher_el, "DATE").text = vch_date_str
        if voucher.get("voucher_number"):
            ET.SubElement(voucher_el, "VOUCHERNUMBER").text = str(voucher["voucher_number"])
        if voucher.get("party_name"):
            ET.SubElement(voucher_el, "PARTYLEDGERNAME").text = voucher["party_name"]
        if voucher.get("narration"):
            ET.SubElement(voucher_el, "NARRATION").text = voucher["narration"]

        for line in voucher.get("lines", []):
            entry = ET.SubElement(voucher_el, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(entry, "LEDGERNAME").text = line.get("ledger", line.get("ledger_name", ""))
            amount = Decimal(str(line.get("amount", line.get("debit", 0) or line.get("credit", 0))))
            if line.get("debit", 0):
                ET.SubElement(entry, "ISDEEMEDPOSITIVE").text = "Yes"
                ET.SubElement(entry, "AMOUNT").text = f"-{amount}"
            else:
                ET.SubElement(entry, "ISDEEMEDPOSITIVE").text = "No"
                ET.SubElement(entry, "AMOUNT").text = str(amount)

        for inv_line in voucher.get("inventory_lines", []):
            inv = ET.SubElement(voucher_el, "ALLINVENTORYENTRIES.LIST")
            ET.SubElement(inv, "STOCKITEMNAME").text = inv_line.get("item_name", "")
            ET.SubElement(inv, "ACTUALQTY").text = str(inv_line.get("quantity", 1))
            ET.SubElement(inv, "RATE").text = str(inv_line.get("rate", 0))
            ET.SubElement(inv, "AMOUNT").text = str(inv_line.get("amount", 0))

        return cls._envelope("Import", "Vouchers", [voucher_el])
