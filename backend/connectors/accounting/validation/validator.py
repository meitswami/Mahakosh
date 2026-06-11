import re
from decimal import Decimal
from typing import Any

from backend.connectors.accounting.base.types import ValidationIssue, ValidationResult

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
HSN_PATTERN = re.compile(r"^[0-9]{4,8}$")
VALID_GST_RATES = {0, 0.25, 3, 5, 12, 18, 28}


class AccountingValidator:
    """Validate vouchers, GST, HSN, and mapping before export."""

    @classmethod
    def validate_gstin(cls, gstin: str | None, label: str = "GSTIN") -> list[ValidationIssue]:
        if not gstin:
            return [ValidationIssue(code="GSTIN_MISSING", message=f"{label} is missing", severity="warning")]
        if not GSTIN_PATTERN.match(gstin.upper()):
            return [ValidationIssue(code="GSTIN_INVALID", message=f"{label} format invalid: {gstin}", field="gstin")]
        return []

    @classmethod
    def validate_hsn(cls, hsn: str | None) -> list[ValidationIssue]:
        if not hsn:
            return [ValidationIssue(code="HSN_MISSING", message="HSN code missing", severity="warning", field="hsn_code")]
        if not HSN_PATTERN.match(hsn):
            return [ValidationIssue(code="HSN_INVALID", message=f"Invalid HSN format: {hsn}", field="hsn_code")]
        return []

    @classmethod
    def validate_gst_rate(cls, rate: float | None) -> list[ValidationIssue]:
        if rate is None:
            return [ValidationIssue(code="GST_RATE_MISSING", message="GST rate not specified", severity="warning")]
        if float(rate) not in VALID_GST_RATES:
            return [ValidationIssue(
                code="GST_RATE_UNUSUAL",
                message=f"GST rate {rate}% is non-standard (expected: {sorted(VALID_GST_RATES)})",
                severity="warning",
                field="gst_rate",
            )]
        return []

    @classmethod
    def validate_tax_amounts(
        cls,
        subtotal: float,
        cgst: float,
        sgst: float,
        igst: float,
        gst_rate: float,
        inter_state: bool = False,
    ) -> list[ValidationIssue]:
        issues = []
        expected_tax = Decimal(str(subtotal)) * Decimal(str(gst_rate)) / Decimal("100")
        actual_tax = Decimal(str(cgst)) + Decimal(str(sgst)) + Decimal(str(igst))
        tolerance = Decimal("1.00")

        if abs(actual_tax - expected_tax) > tolerance:
            issues.append(ValidationIssue(
                code="TAX_MISMATCH",
                message=f"Tax total ₹{actual_tax} differs from expected ₹{expected_tax:.2f} at {gst_rate}%",
                field="tax_amounts",
            ))

        if inter_state and (cgst > 0 or sgst > 0):
            issues.append(ValidationIssue(
                code="INTERSTATE_CGST_SGST",
                message="Inter-state transaction should use IGST, not CGST/SGST",
                field="igst_amount",
            ))
        if not inter_state and igst > 0:
            issues.append(ValidationIssue(
                code="INTRASTATE_IGST",
                message="Intra-state transaction should use CGST/SGST, not IGST",
                field="igst_amount",
            ))
        return issues

    @classmethod
    def validate_voucher_draft(cls, voucher: dict[str, Any]) -> ValidationResult:
        issues: list[ValidationIssue] = []
        checks_passed: list[str] = []

        if not voucher.get("voucher_type"):
            issues.append(ValidationIssue(code="VCH_TYPE_MISSING", message="Voucher type is required"))
        else:
            checks_passed.append("voucher_type_present")

        if not voucher.get("party_name") and voucher.get("voucher_type") in ("Purchase", "Sales"):
            issues.append(ValidationIssue(code="PARTY_MISSING", message="Party name required", severity="warning"))
        else:
            checks_passed.append("party_present")

        issues.extend(cls.validate_gstin(voucher.get("party_gstin"), "Party GSTIN"))

        lines = voucher.get("lines", [])
        total_debit = sum(l.get("debit", 0) for l in lines)
        total_credit = sum(l.get("credit", 0) for l in lines)
        if lines and abs(total_debit - total_credit) > 0.01:
            issues.append(ValidationIssue(
                code="UNBALANCED",
                message=f"Debit ₹{total_debit:.2f} ≠ Credit ₹{total_credit:.2f}",
            ))
        elif lines:
            checks_passed.append("double_entry_balanced")

        subtotal = voucher.get("subtotal", 0)
        if subtotal:
            issues.extend(cls.validate_tax_amounts(
                subtotal,
                voucher.get("cgst_amount", 0),
                voucher.get("sgst_amount", 0),
                voucher.get("igst_amount", 0),
                voucher.get("gst_rate", 18),
                voucher.get("inter_state", False),
            ))

        for inv_line in voucher.get("inventory_lines", []):
            issues.extend(cls.validate_hsn(inv_line.get("hsn_code")))

        is_valid = not any(i.severity == "error" for i in issues)
        confidence = max(0, 100 - len(issues) * 10)
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            checks_passed=checks_passed,
            confidence=confidence,
            reasoning=f"{len(checks_passed)} checks passed, {len(issues)} issues found",
        )

    @classmethod
    def to_dict(cls, result: ValidationResult) -> dict[str, Any]:
        return {
            "is_valid": result.is_valid,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity, "field": i.field}
                for i in result.issues
            ],
            "checks_passed": result.checks_passed,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }
