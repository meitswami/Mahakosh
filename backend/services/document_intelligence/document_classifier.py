import re
from typing import Any

from backend.services.document_intelligence.types import ClassificationResult, DocumentClass

CLASSIFICATION_PATTERNS: dict[DocumentClass, list[tuple[str, float]]] = {
    DocumentClass.GST_INVOICE: [
        (r"\bgst\s*invo?ice\b", 0.95),
        (r"\btax\s*invo?ice\b", 0.90),
        (r"\bgstin\b", 0.70),
        (r"\bcgst\b|\bsgst\b|\bigst\b", 0.75),
        (r"\bhsn\s*/?\s*sac\b", 0.65),
    ],
    DocumentClass.PURCHASE_INVOICE: [
        (r"\bpurchase\s*invo?ice\b", 0.95),
        (r"\bbill\s*of\s*supply\b", 0.80),
        (r"\bvendor\b|\bsupplier\b", 0.55),
    ],
    DocumentClass.SALES_INVOICE: [
        (r"\bsales\s*invo?ice\b", 0.95),
        (r"\btax\s*invo?ice\s*to\b", 0.70),
        (r"\bcustomer\b|\bbuyer\b", 0.50),
    ],
    DocumentClass.INVOICE: [
        (r"\binvo?ice\b", 0.85),
        (r"\binvo?ice\s*no\.?", 0.80),
        (r"\bbill\s*no\.?", 0.60),
    ],
    DocumentClass.DELIVERY_CHALLAN: [
        (r"\bdelivery\s*challan\b", 0.95),
        (r"\bd\.?c\.?\s*no\b", 0.75),
        (r"\bchallan\s*no\b", 0.80),
    ],
    DocumentClass.QUOTATION: [
        (r"\bquotation\b", 0.95),
        (r"\bquote\s*no\b", 0.85),
        (r"\bestimate\b", 0.70),
        (r"\bproforma\b", 0.65),
    ],
    DocumentClass.BANK_STATEMENT: [
        (r"\bbank\s*statement\b", 0.95),
        (r"\baccount\s*statement\b", 0.90),
        (r"\bifsc\b", 0.70),
        (r"\bopening\s*balance\b", 0.65),
        (r"\bclosing\s*balance\b", 0.65),
        (r"\bneft\b|\brtgs\b|\bimps\b|\bupi\b", 0.55),
    ],
    DocumentClass.LEDGER: [
        (r"\bledger\b", 0.90),
        (r"\baccount\s*ledger\b", 0.85),
        (r"\btrial\s*balance\b", 0.80),
        (r"\bdebit\b.*\bcredit\b", 0.60),
    ],
    DocumentClass.PURCHASE_ORDER: [
        (r"\bpurchase\s*order\b", 0.95),
        (r"\bp\.?o\.?\s*no\b", 0.85),
        (r"\bpo\s*number\b", 0.80),
    ],
}


class DocumentClassifier:
    """Classifies Indian business documents from OCR text using pattern signals."""

    def classify(self, text: str, metadata: dict[str, Any] | None = None) -> ClassificationResult:
        normalized = self._normalize_text(text)
        scores: dict[DocumentClass, float] = {cls: 0.0 for cls in DocumentClass}
        signals: dict[str, float] = {}

        for doc_class, patterns in CLASSIFICATION_PATTERNS.items():
            for pattern, weight in patterns:
                if re.search(pattern, normalized, re.IGNORECASE):
                    scores[doc_class] = max(scores[doc_class], weight)
                    signals[f"{doc_class.value}:{pattern[:30]}"] = weight

        if metadata:
            mime = metadata.get("mime_type", "")
            filename = metadata.get("file_name", "").lower()
            if "invoice" in filename:
                scores[DocumentClass.INVOICE] = max(scores[DocumentClass.INVOICE], 0.75)
            if "challan" in filename:
                scores[DocumentClass.DELIVERY_CHALLAN] = max(scores[DocumentClass.DELIVERY_CHALLAN], 0.80)
            if "statement" in filename:
                scores[DocumentClass.BANK_STATEMENT] = max(scores[DocumentClass.BANK_STATEMENT], 0.75)

        best_class = DocumentClass.UNKNOWN
        best_score = 0.0

        for doc_class, score in scores.items():
            if doc_class != DocumentClass.UNKNOWN and score > best_score:
                best_score = score
                best_class = doc_class

        if best_score < 0.45:
            best_class = DocumentClass.UNKNOWN
            best_score = max(best_score, 0.3)

        if best_class in (DocumentClass.INVOICE, DocumentClass.GST_INVOICE):
            if scores[DocumentClass.GST_INVOICE] >= 0.65:
                best_class = DocumentClass.GST_INVOICE
                best_score = scores[DocumentClass.GST_INVOICE]
            elif scores[DocumentClass.PURCHASE_INVOICE] >= 0.55:
                best_class = DocumentClass.PURCHASE_INVOICE
                best_score = scores[DocumentClass.PURCHASE_INVOICE]
            elif scores[DocumentClass.SALES_INVOICE] >= 0.55:
                best_class = DocumentClass.SALES_INVOICE
                best_score = scores[DocumentClass.SALES_INVOICE]

        return ClassificationResult(
            document_class=best_class,
            confidence=round(min(best_score, 1.0), 4),
            signals=signals,
        )

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()
