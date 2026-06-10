import re
import uuid
from decimal import Decimal, InvalidOperation

from backend.services.document_intelligence.types import (
    ConsensusResult,
    ExtractedField,
    ExtractedTable,
    LayoutRegion,
)


class FieldExtractor:
    """Extracts structured invoice fields from OCR consensus output and tables."""

    GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", re.I)
    HSN_RE = re.compile(r"\b(\d{4,8})\b")
    AMOUNT_RE = re.compile(r"(?:rs\.?|₹|inr)?\s*([\d,]+\.?\d*)", re.I)
    DATE_RE = re.compile(
        r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
        re.I,
    )

    FIELD_DEFINITIONS: dict[str, dict] = {
        "invoice_number": {"patterns": [
            re.compile(r"(?:invoice|inv|bill)\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9\-/]+)", re.I),
            re.compile(r"\b(?:inv|bill)\s*[#:.]?\s*([A-Z0-9\-/]{3,20})", re.I),
        ]},
        "invoice_date": {"patterns": [
            re.compile(r"(?:invoice|bill)\s*date\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", re.I),
            re.compile(r"\bdate\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", re.I),
        ]},
        "vendor_name": {"patterns": [
            re.compile(r"(?:from|seller|supplier|vendor|sold\s*by)\s*[:\-]?\s*(.+?)(?:\n|gstin|address)", re.I),
        ]},
        "customer_name": {"patterns": [
            re.compile(r"(?:to|buyer|customer|bill\s*to|ship\s*to)\s*[:\-]?\s*(.+?)(?:\n|gstin|address)", re.I),
        ]},
        "gstin": {"patterns": [GSTIN_RE]},
        "subtotal": {"patterns": [
            re.compile(r"(?:sub\s*total|taxable\s*(?:value|amount))\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ]},
        "cgst": {"patterns": [
            re.compile(r"\bcgst\s*(?:@\s*\d+%?)?\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ]},
        "sgst": {"patterns": [
            re.compile(r"\bsgst\s*(?:@\s*\d+%?)?\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ]},
        "igst": {"patterns": [
            re.compile(r"\bigst\s*(?:@\s*\d+%?)?\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ]},
        "gst_amount": {"patterns": [
            re.compile(r"(?:total\s*tax|gst\s*amount)\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ]},
        "grand_total": {"patterns": [
            re.compile(r"(?:grand\s*total|total\s*amount|net\s*(?:amount|payable)|amount\s*payable)\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ]},
    }

    def extract(
        self,
        consensus: ConsensusResult,
        layout_regions: list[LayoutRegion],
        tables: list[ExtractedTable],
        field_comparisons: dict | None = None,
    ) -> list[ExtractedField]:
        text = consensus.final_output.full_text
        fields: list[ExtractedField] = []

        for field_name, definition in self.FIELD_DEFINITIONS.items():
            value, confidence, source = self._extract_field(field_name, definition["patterns"], text)

            if field_comparisons and field_name in field_comparisons:
                comparison = field_comparisons[field_name]
                if comparison.get("consensus_value"):
                    value = comparison["consensus_value"]
                    confidence = comparison.get("confidence", confidence)
                    source = comparison.get("selected_engine", source)

            fields.append(ExtractedField(
                field_name=field_name,
                field_value=value,
                confidence=confidence,
                source_engine=source,
                alternatives=self._build_alternatives(field_comparisons, field_name),
            ))

        gstin_matches = self.GSTIN_RE.findall(text)
        if len(gstin_matches) >= 2:
            fields.append(ExtractedField(
                field_name="vendor_gstin",
                field_value=gstin_matches[0].upper(),
                confidence=0.85,
                source_engine="consensus",
            ))
            fields.append(ExtractedField(
                field_name="customer_gstin",
                field_value=gstin_matches[1].upper(),
                confidence=0.80,
                source_engine="consensus",
            ))

        line_item_fields = self._extract_line_items_from_tables(tables)
        fields.extend(line_item_fields)

        hsn_codes = list(dict.fromkeys(self.HSN_RE.findall(text)))[:50]
        if hsn_codes:
            fields.append(ExtractedField(
                field_name="hsn_codes",
                field_value=",".join(hsn_codes),
                confidence=0.70,
                source_engine="consensus",
            ))

        return fields

    def _extract_field(
        self,
        field_name: str,
        patterns: list[re.Pattern],
        text: str,
    ) -> tuple[str | None, float, str | None]:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                return value.strip(), 0.80, "consensus"
        return None, 0.0, None

    def _extract_line_items_from_tables(self, tables: list[ExtractedTable]) -> list[ExtractedField]:
        fields: list[ExtractedField] = []
        for table in tables:
            if table.table_type not in ("line_items", "gst_table"):
                continue

            for row_idx, row in enumerate(table.rows[:100]):
                item_data = self._parse_line_item_row(table.headers, row)
                if not item_data.get("description"):
                    continue
                for key, val in item_data.items():
                    fields.append(ExtractedField(
                        field_name=f"line_{row_idx}_{key}",
                        field_value=str(val) if val is not None else None,
                        confidence=table.confidence,
                        source_engine=table.extraction_method,
                        page_number=table.page_number,
                    ))
        return fields

    def _parse_line_item_row(self, headers: list[str], row: list[str]) -> dict:
        header_map = {h.lower().strip(): i for i, h in enumerate(headers)}
        result: dict = {}

        col_mappings = {
            "description": ["description", "particulars", "item", "product"],
            "hsn_code": ["hsn", "hsn/sac", "sac", "hsn code"],
            "quantity": ["qty", "quantity", "qnty"],
            "rate": ["rate", "price", "unit price"],
            "amount": ["amount", "value", "total"],
            "unit": ["unit", "uom"],
            "gst_rate": ["gst%", "gst rate", "tax%"],
        }

        for field, candidates in col_mappings.items():
            for candidate in candidates:
                for header, idx in header_map.items():
                    if candidate in header and idx < len(row):
                        result[field] = row[idx].strip()
                        break
                if field in result:
                    break

        if not result.get("description") and row:
            result["description"] = row[0].strip()

        return result

    def _build_alternatives(self, comparisons: dict | None, field_name: str) -> list[dict]:
        if not comparisons or field_name not in comparisons:
            return []
        comp = comparisons[field_name]
        alts = []
        if comp.get("paddle_value"):
            alts.append({"engine": "paddleocr", "value": comp["paddle_value"]})
        if comp.get("surya_value"):
            alts.append({"engine": "surya", "value": comp["surya_value"]})
        return alts

    @staticmethod
    def parse_amount(value: str | None) -> Decimal | None:
        if not value:
            return None
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
