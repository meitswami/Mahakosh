from backend.services.document_intelligence.types import BoundingBox, LayoutRegion, OCREngineOutput, OCRToken


class LayoutAnalyzer:
    """Detects structural regions in OCR output: headers, tables, GST blocks, totals, etc."""

    REGION_KEYWORDS: dict[str, list[str]] = {
        "header": ["tax invoice", "invoice", "bill of supply", "delivery challan", "quotation"],
        "footer": ["terms and conditions", "authorized signatory", "for ", "thank you", "e.&o.e"],
        "gst_block": ["gstin", "cgst", "sgst", "igst", "hsn", "sac", "taxable value"],
        "totals": ["grand total", "total amount", "net amount", "amount payable", "round off"],
        "address": ["address", "pin code", "pincode", "state", "city", "phone", "mobile"],
        "signature": ["signature", "signatory", "authorised", "authorized"],
        "stamp": ["stamp", "seal"],
        "line_items": ["description", "particulars", "item", "qty", "quantity", "rate", "amount", "hsn"],
    }

    def analyze(self, ocr_output: OCREngineOutput) -> list[LayoutRegion]:
        regions: list[LayoutRegion] = []

        for page in ocr_output.pages:
            if not page.tokens:
                continue

            page_height = page.height or 1
            header_tokens = [t for t in page.tokens if t.bbox.y1 < page_height * 0.15]
            footer_tokens = [t for t in page.tokens if t.bbox.y1 > page_height * 0.85]
            body_tokens = [t for t in page.tokens if t not in header_tokens and t not in footer_tokens]

            if header_tokens:
                regions.append(self._build_region("header", header_tokens, page.page_number))

            if footer_tokens:
                regions.append(self._build_region("footer", footer_tokens, page.page_number))

            gst_tokens = self._filter_by_keywords(page.tokens, self.REGION_KEYWORDS["gst_block"])
            if gst_tokens:
                regions.append(self._build_region("gst_block", gst_tokens, page.page_number))

            total_tokens = self._filter_by_keywords(page.tokens, self.REGION_KEYWORDS["totals"])
            if total_tokens:
                regions.append(self._build_region("totals", total_tokens, page.page_number))

            address_tokens = self._filter_by_keywords(body_tokens, self.REGION_KEYWORDS["address"])
            if address_tokens:
                regions.append(self._build_region("address", address_tokens, page.page_number))

            line_item_tokens = self._detect_line_item_region(body_tokens, page.page_number)
            if line_item_tokens:
                regions.append(line_item_tokens)

            table_region = self._detect_table_region(body_tokens, page.page_number)
            if table_region:
                regions.append(table_region)

        return regions

    def _filter_by_keywords(self, tokens: list[OCRToken], keywords: list[str]) -> list[OCRToken]:
        matched: list[OCRToken] = []
        for token in tokens:
            text_lower = token.text.lower()
            if any(kw in text_lower for kw in keywords):
                matched.append(token)
        return matched

    def _build_region(self, region_type: str, tokens: list[OCRToken], page_number: int) -> LayoutRegion:
        bbox = self._merge_bboxes([t.bbox for t in tokens])
        text = " ".join(t.text for t in tokens)
        confidence = sum(t.confidence for t in tokens) / len(tokens)
        return LayoutRegion(
            region_type=region_type,
            bbox=bbox,
            text=text,
            confidence=round(confidence, 4),
            page_number=page_number,
        )

    def _merge_bboxes(self, bboxes: list[BoundingBox]) -> BoundingBox:
        return BoundingBox(
            x1=min(b.x1 for b in bboxes),
            y1=min(b.y1 for b in bboxes),
            x2=max(b.x2 for b in bboxes),
            y2=max(b.y2 for b in bboxes),
        )

    def _detect_line_item_region(self, tokens: list[OCRToken], page_number: int) -> LayoutRegion | None:
        header_keywords = self.REGION_KEYWORDS["line_items"]
        header_tokens = [t for t in tokens if any(kw in t.text.lower() for kw in header_keywords)]
        if len(header_tokens) < 2:
            return None

        y_start = min(t.bbox.y1 for t in header_tokens)
        line_tokens = [t for t in tokens if t.bbox.y1 >= y_start]
        if len(line_tokens) < 3:
            return None

        return self._build_region("line_items", line_tokens, page_number)

    def _detect_table_region(self, tokens: list[OCRToken], page_number: int) -> LayoutRegion | None:
        if len(tokens) < 6:
            return None

        rows: dict[int, list[OCRToken]] = {}
        for token in tokens:
            row_key = int(token.bbox.y1 / 20)
            rows.setdefault(row_key, []).append(token)

        table_rows = [row for row in rows.values() if len(row) >= 3]
        if len(table_rows) < 2:
            return None

        table_tokens = [t for row in table_rows for t in row]
        region = self._build_region("table", table_tokens, page_number)
        region.metadata["row_count"] = len(table_rows)
        region.metadata["column_estimate"] = max(len(row) for row in table_rows)
        return region
