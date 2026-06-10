import re
from datetime import datetime
from decimal import Decimal

from backend.services.document_intelligence.types import (
    ExtractedField,
    ExtractedTable,
    ValidationIssue,
    ValidationReport,
)
from backend.services.document_intelligence.field_extractor import FieldExtractor


class DocumentValidator:
    """Validates extracted document fields for Indian business compliance."""

    GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

    def validate(
        self,
        fields: list[ExtractedField],
        tables: list[ExtractedTable],
    ) -> ValidationReport:
        field_map = {f.field_name: f for f in fields}
        issues: list[ValidationIssue] = []
        passed: list[str] = []
        failed: list[str] = []

        self._validate_invoice_number(field_map, issues, passed, failed)
        self._validate_invoice_date(field_map, issues, passed, failed)
        self._validate_gstin(field_map, issues, passed, failed)
        self._validate_amounts(field_map, issues, passed, failed)
        self._validate_tax_consistency(field_map, issues, passed, failed)
        self._validate_required_fields(field_map, issues, passed, failed)
        self._validate_tables(tables, issues, passed, failed)

        is_valid = len([i for i in issues if i.severity == "error"]) == 0
        return ValidationReport(
            is_valid=is_valid,
            issues=issues,
            checks_passed=passed,
            checks_failed=failed,
        )

    def _validate_invoice_number(
        self, fields: dict, issues: list, passed: list, failed: list
    ) -> None:
        inv = fields.get("invoice_number")
        if inv and inv.field_value:
            passed.append("invoice_number_present")
        else:
            issues.append(ValidationIssue(
                code="MISSING_INVOICE_NUMBER",
                severity="error",
                message="Invoice number not found in document",
                field_name="invoice_number",
            ))
            failed.append("invoice_number_present")

    def _validate_invoice_date(
        self, fields: dict, issues: list, passed: list, failed: list
    ) -> None:
        date_field = fields.get("invoice_date")
        if not date_field or not date_field.field_value:
            issues.append(ValidationIssue(
                code="MISSING_INVOICE_DATE",
                severity="warning",
                message="Invoice date not found",
                field_name="invoice_date",
            ))
            failed.append("invoice_date_format")
            return

        if self._parse_date(date_field.field_value):
            passed.append("invoice_date_format")
        else:
            issues.append(ValidationIssue(
                code="INVALID_DATE_FORMAT",
                severity="warning",
                message=f"Could not parse date: {date_field.field_value}",
                field_name="invoice_date",
            ))
            failed.append("invoice_date_format")

    def _validate_gstin(
        self, fields: dict, issues: list, passed: list, failed: list
    ) -> None:
        for gstin_field_name in ("gstin", "vendor_gstin", "customer_gstin"):
            gstin_field = fields.get(gstin_field_name)
            if not gstin_field or not gstin_field.field_value:
                continue
            value = gstin_field.field_value.replace(" ", "").upper()
            if self.GSTIN_PATTERN.match(value):
                passed.append(f"gstin_format_{gstin_field_name}")
            else:
                issues.append(ValidationIssue(
                    code="INVALID_GSTIN_FORMAT",
                    severity="error",
                    message=f"Invalid GSTIN format: {value}",
                    field_name=gstin_field_name,
                ))
                failed.append(f"gstin_format_{gstin_field_name}")

    def _validate_amounts(
        self, fields: dict, issues: list, passed: list, failed: list
    ) -> None:
        grand_total = fields.get("grand_total")
        if grand_total and grand_total.field_value:
            amount = FieldExtractor.parse_amount(grand_total.field_value)
            if amount is not None and amount > 0:
                passed.append("grand_total_valid")
            else:
                issues.append(ValidationIssue(
                    code="INVALID_GRAND_TOTAL",
                    severity="error",
                    message="Grand total is missing or zero",
                    field_name="grand_total",
                ))
                failed.append("grand_total_valid")
        else:
            issues.append(ValidationIssue(
                code="MISSING_GRAND_TOTAL",
                severity="error",
                message="Grand total not found",
                field_name="grand_total",
            ))
            failed.append("grand_total_valid")

    def _validate_tax_consistency(
        self, fields: dict, issues: list, passed: list, failed: list
    ) -> None:
        subtotal = FieldExtractor.parse_amount(
            fields.get("subtotal", ExtractedField("subtotal", None, 0)).field_value
        )
        cgst = FieldExtractor.parse_amount(fields.get("cgst", ExtractedField("cgst", None, 0)).field_value)
        sgst = FieldExtractor.parse_amount(fields.get("sgst", ExtractedField("sgst", None, 0)).field_value)
        igst = FieldExtractor.parse_amount(fields.get("igst", ExtractedField("igst", None, 0)).field_value)
        grand = FieldExtractor.parse_amount(
            fields.get("grand_total", ExtractedField("grand_total", None, 0)).field_value
        )

        if subtotal is None or grand is None:
            return

        tax_total = (cgst or Decimal(0)) + (sgst or Decimal(0)) + (igst or Decimal(0))
        expected = subtotal + tax_total
        tolerance = Decimal("2.00")

        if abs(expected - grand) <= tolerance:
            passed.append("amount_consistency")
        else:
            issues.append(ValidationIssue(
                code="AMOUNT_MISMATCH",
                severity="warning",
                message=f"Subtotal ({subtotal}) + Tax ({tax_total}) != Grand Total ({grand})",
            ))
            failed.append("amount_consistency")

        if cgst and sgst and abs(cgst - sgst) > Decimal("0.05"):
            issues.append(ValidationIssue(
                code="CGST_SGST_MISMATCH",
                severity="warning",
                message=f"CGST ({cgst}) and SGST ({sgst}) should be equal for intra-state",
            ))
            failed.append("tax_consistency")
        elif cgst and sgst:
            passed.append("tax_consistency")

    def _validate_required_fields(
        self, fields: dict, issues: list, passed: list, failed: list
    ) -> None:
        required = ["invoice_number", "grand_total"]
        for req in required:
            f = fields.get(req)
            if f and f.field_value:
                passed.append(f"required_{req}")
            else:
                failed.append(f"required_{req}")

    def _validate_tables(
        self, tables: list[ExtractedTable], issues: list, passed: list, failed: list
    ) -> None:
        line_item_tables = [t for t in tables if t.table_type == "line_items"]
        if line_item_tables:
            passed.append("line_items_table_found")
        else:
            issues.append(ValidationIssue(
                code="NO_LINE_ITEMS",
                severity="info",
                message="No line item table detected",
            ))

    def _parse_date(self, value: str) -> datetime | None:
        formats = ["%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"]
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        return None
