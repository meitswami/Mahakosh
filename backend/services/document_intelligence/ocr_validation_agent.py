import re
from typing import Any

from backend.services.document_intelligence.types import OCREngineOutput


class OCRValidationAgent:
    """Compares PaddleOCR and Surya outputs; selects most reliable field values."""

    GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
    AMOUNT_PATTERN = re.compile(r"[\d,]+\.?\d*")
    DATE_PATTERN = re.compile(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b")

    FIELD_PATTERNS: dict[str, list[re.Pattern]] = {
        "invoice_number": [
            re.compile(r"(?:invoice|inv|bill)\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9\-/]+)", re.I),
            re.compile(r"\b(?:inv|bill)\s*[#:]?\s*([A-Z0-9\-/]{3,})", re.I),
        ],
        "invoice_date": [
            re.compile(r"(?:invoice|bill)\s*date\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", re.I),
            re.compile(r"date\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", re.I),
        ],
        "gstin": [GSTIN_PATTERN],
        "grand_total": [
            re.compile(r"(?:grand\s*total|total\s*amount|net\s*amount)\s*[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I),
        ],
        "cgst": [re.compile(r"\bcgst\s*[:\-@]?\s*(?:\d+%?\s*)?[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I)],
        "sgst": [re.compile(r"\bsgst\s*[:\-@]?\s*(?:\d+%?\s*)?[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I)],
        "igst": [re.compile(r"\bigst\s*[:\-@]?\s*(?:\d+%?\s*)?[:\-]?\s*(?:rs\.?|₹)?\s*([\d,]+\.?\d*)", re.I)],
        "vendor_name": [
            re.compile(r"(?:from|seller|supplier|vendor)\s*[:\-]?\s*(.+?)(?:\n|gstin)", re.I),
        ],
        "customer_name": [
            re.compile(r"(?:to|buyer|customer|bill\s*to)\s*[:\-]?\s*(.+?)(?:\n|gstin)", re.I),
        ],
    }

    def compare_outputs(
        self,
        paddle_output: OCREngineOutput,
        surya_output: OCREngineOutput,
    ) -> dict[str, Any]:
        paddle_fields = self._extract_quick_fields(paddle_output.full_text)
        surya_fields = self._extract_quick_fields(surya_output.full_text)

        all_fields = set(paddle_fields.keys()) | set(surya_fields.keys())
        comparisons: dict[str, Any] = {}

        for field_name in all_fields:
            paddle_val = paddle_fields.get(field_name)
            surya_val = surya_fields.get(field_name)
            comparison = self._compare_field(field_name, paddle_val, surya_val, paddle_output, surya_output)
            comparisons[field_name] = comparison

        return {
            "field_comparisons": comparisons,
            "paddle_confidence": self._avg_confidence(paddle_output),
            "surya_confidence": self._avg_confidence(surya_output),
            "text_similarity": self._text_similarity(paddle_output.full_text, surya_output.full_text),
        }

    def _extract_quick_fields(self, text: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for field_name, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    value = match.group(1) if match.lastindex else match.group(0)
                    fields[field_name] = value.strip()
                    break
        return fields

    def _compare_field(
        self,
        field_name: str,
        paddle_val: str | None,
        surya_val: str | None,
        paddle_output: OCREngineOutput,
        surya_output: OCREngineOutput,
    ) -> dict[str, Any]:
        if paddle_val is None and surya_val is None:
            return {
                "paddle_value": None,
                "surya_value": None,
                "consensus_value": None,
                "selected_engine": None,
                "confidence": 0.0,
                "reason": "not_found",
            }

        if paddle_val is None:
            return {
                "paddle_value": None,
                "surya_value": surya_val,
                "consensus_value": surya_val,
                "selected_engine": "surya",
                "confidence": 0.75,
                "reason": "only_surya_found",
            }

        if surya_val is None:
            return {
                "paddle_value": paddle_val,
                "surya_value": None,
                "consensus_value": paddle_val,
                "selected_engine": "paddleocr",
                "confidence": 0.75,
                "reason": "only_paddle_found",
            }

        normalized_paddle = self._normalize_value(field_name, paddle_val)
        normalized_surya = self._normalize_value(field_name, surya_val)

        if normalized_paddle == normalized_surya:
            return {
                "paddle_value": paddle_val,
                "surya_value": surya_val,
                "consensus_value": paddle_val,
                "selected_engine": "both_agree",
                "confidence": 0.95,
                "reason": "engines_agree",
            }

        paddle_score = self._field_reliability_score(field_name, paddle_val, paddle_output)
        surya_score = self._field_reliability_score(field_name, surya_val, surya_output)

        if paddle_score >= surya_score:
            selected_engine = "paddleocr"
            consensus = paddle_val
            confidence = paddle_score
        else:
            selected_engine = "surya"
            consensus = surya_val
            confidence = surya_score

        return {
            "paddle_value": paddle_val,
            "surya_value": surya_val,
            "consensus_value": consensus,
            "selected_engine": selected_engine,
            "confidence": round(confidence, 4),
            "reason": "confidence_selection",
        }

    def _normalize_value(self, field_name: str, value: str) -> str:
        value = value.strip().upper()
        if field_name in ("grand_total", "cgst", "sgst", "igst", "subtotal"):
            return re.sub(r"[^\d.]", "", value)
        if field_name == "gstin":
            return value.replace(" ", "")
        return value

    def _field_reliability_score(
        self,
        field_name: str,
        value: str,
        output: OCREngineOutput,
    ) -> float:
        base = output.pages[0].average_confidence if output.pages else 0.5

        if field_name == "gstin" and self.GSTIN_PATTERN.fullmatch(value.replace(" ", "").upper()):
            base += 0.15
        if field_name in ("grand_total", "cgst", "sgst", "igst") and self.AMOUNT_PATTERN.search(value):
            base += 0.10
        if field_name == "invoice_date" and self.DATE_PATTERN.search(value):
            base += 0.10

        return min(base, 1.0)

    def _avg_confidence(self, output: OCREngineOutput) -> float:
        if not output.pages:
            return 0.0
        return sum(p.average_confidence for p in output.pages) / len(output.pages)

    def _text_similarity(self, text_a: str, text_b: str) -> float:
        import difflib
        return round(difflib.SequenceMatcher(None, text_a, text_b).ratio(), 4)
