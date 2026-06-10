import uuid
from pathlib import Path

from backend.services.document_intelligence.types import BoundingBox, ExtractedTable


class TableExtractor:
    """Extracts tables from PDFs and OCR-aligned regions using pdfplumber, camelot, and tabula."""

    def extract_from_pdf(self, pdf_path: str) -> list[ExtractedTable]:
        tables: list[ExtractedTable] = []
        path = Path(pdf_path)

        if not path.exists() or path.suffix.lower() != ".pdf":
            return tables

        tables.extend(self._extract_with_pdfplumber(pdf_path))
        tables.extend(self._extract_with_camelot(pdf_path))
        tables.extend(self._extract_with_tabula(pdf_path))

        return self._deduplicate_tables(tables)

    def extract_from_layout(
        self,
        layout_regions: list,
        ocr_text_by_page: dict[int, str],
    ) -> list[ExtractedTable]:
        tables: list[ExtractedTable] = []
        for region in layout_regions:
            if region.region_type not in ("table", "line_items"):
                continue

            rows = self._parse_text_table(region.text)
            if not rows:
                continue

            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            table_type = "line_items" if region.region_type == "line_items" else "general"

            tables.append(ExtractedTable(
                table_id=str(uuid.uuid4()),
                table_type=table_type,
                page_number=region.page_number,
                headers=headers,
                rows=data_rows,
                bbox=region.bbox,
                confidence=region.confidence,
                extraction_method="layout_ocr",
                raw_data={"source_text": region.text[:2000]},
            ))

        return tables

    def _extract_with_pdfplumber(self, pdf_path: str) -> list[ExtractedTable]:
        tables: list[ExtractedTable] = []
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    extracted = page.extract_tables()
                    for table_data in extracted or []:
                        if not table_data or len(table_data) < 2:
                            continue
                        headers = [str(c or "") for c in table_data[0]]
                        rows = [[str(c or "") for c in row] for row in table_data[1:]]
                        table_type = self._classify_table(headers, rows)
                        tables.append(ExtractedTable(
                            table_id=str(uuid.uuid4()),
                            table_type=table_type,
                            page_number=page_num,
                            headers=headers,
                            rows=rows,
                            confidence=0.85,
                            extraction_method="pdfplumber",
                        ))
        except Exception:
            pass
        return tables

    def _extract_with_camelot(self, pdf_path: str) -> list[ExtractedTable]:
        tables: list[ExtractedTable] = []
        try:
            import camelot

            for flavor in ("lattice", "stream"):
                result = camelot.read_pdf(pdf_path, flavor=flavor, pages="all")
                for table in result:
                    df = table.df
                    if df.shape[0] < 2:
                        continue
                    headers = [str(v) for v in df.iloc[0].tolist()]
                    rows = [[str(v) for v in row] for row in df.iloc[1:].values.tolist()]
                    tables.append(ExtractedTable(
                        table_id=str(uuid.uuid4()),
                        table_type=self._classify_table(headers, rows),
                        page_number=int(table.page),
                        headers=headers,
                        rows=rows,
                        confidence=float(table.accuracy) / 100 if hasattr(table, "accuracy") else 0.75,
                        extraction_method=f"camelot_{flavor}",
                        raw_data={"parsing_report": str(table.parsing_report) if hasattr(table, "parsing_report") else ""},
                    ))
        except Exception:
            pass
        return tables

    def _extract_with_tabula(self, pdf_path: str) -> list[ExtractedTable]:
        tables: list[ExtractedTable] = []
        try:
            import tabula

            dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
            for page_idx, df in enumerate(dfs, start=1):
                if df is None or df.shape[0] < 2:
                    continue
                headers = [str(v) for v in df.columns.tolist()]
                rows = [[str(v) for v in row] for row in df.values.tolist()]
                tables.append(ExtractedTable(
                    table_id=str(uuid.uuid4()),
                    table_type=self._classify_table(headers, rows),
                    page_number=page_idx,
                    headers=headers,
                    rows=rows,
                    confidence=0.70,
                    extraction_method="tabula",
                ))
        except Exception:
            pass
        return tables

    def _classify_table(self, headers: list[str], rows: list[list[str]]) -> str:
        header_text = " ".join(headers).lower()
        if any(kw in header_text for kw in ("hsn", "cgst", "sgst", "igst", "tax")):
            return "gst_table"
        if any(kw in header_text for kw in ("description", "particulars", "item", "qty", "rate")):
            return "line_items"
        if any(kw in header_text for kw in ("total", "subtotal", "grand")):
            return "summary_table"
        return "general"

    def _parse_text_table(self, text: str) -> list[list[str]]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) < 2:
            return []
        return [line.split() for line in lines]

    def _deduplicate_tables(self, tables: list[ExtractedTable]) -> list[ExtractedTable]:
        seen: set[str] = set()
        unique: list[ExtractedTable] = []
        for table in tables:
            key = f"{table.page_number}:{table.table_type}:{table.headers[:3]}:{len(table.rows)}"
            if key not in seen:
                seen.add(key)
                unique.append(table)
        return unique
