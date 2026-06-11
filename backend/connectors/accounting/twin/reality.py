"""Indian Accounting Reality Framework — rules for messy real-world data."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from backend.connectors.accounting.twin.objects import (
    IssueSeverity,
    NormalizedLedger,
    NormalizedParty,
    NormalizedStockItem,
    NormalizedVoucher,
    TwinObjectBase,
)

# Common Indian ledger name prefixes/suffixes that vary across Tally versions
LEDGER_PREFIX_VARIANTS = [
    (r"^m\s*/\s*s\.?\s*", ""),
    (r"^m/s\.?\s*", ""),
    (r"^ms\.?\s+", ""),
    (r"^shri\.?\s+", ""),
    (r"^sh\.?\s+", ""),
    (r"^smt\.?\s+", ""),
    (r"^mr\.?\s+", ""),
    (r"^mrs\.?\s+", ""),
    (r"^dr\.?\s+", ""),
    (r"^m\s*/\s*s\s+", ""),
]

LEDGER_SUFFIX_VARIANTS = [
    (r"\s+pvt\.?\s*ltd\.?$", " pvt ltd"),
    (r"\s+private\s+limited$", " pvt ltd"),
    (r"\s+ltd\.?$", " ltd"),
    (r"\s+limited$", " ltd"),
    (r"\s+llp$", " llp"),
    (r"\s+&\s+co\.?$", " and co"),
    (r"\s+and\s+company$", " and co"),
]

# Standard GST rates in India
VALID_GST_RATES = {0, 0.25, 3, 5, 12, 18, 28}

# Non-standard voucher type aliases seen in Indian Tally setups
VOUCHER_TYPE_ALIASES = {
    "purc": "purchase",
    "pur": "purchase",
    "purchase invoice": "purchase",
    "sales invoice": "sales",
    "sale": "sales",
    "rcpt": "receipt",
    "pymt": "payment",
    "pmt": "payment",
    "jrnl": "journal",
    "jrn": "journal",
    "cntra": "contra",
    "debit note": "debit_note",
    "credit note": "credit_note",
    "dn": "debit_note",
    "cn": "credit_note",
    "exp": "expense",
    "expense voucher": "expense",
}

# HSN chapter → typical GST rate hints
HSN_GST_HINTS: dict[str, float] = {
    "01": 0, "02": 0, "03": 5, "04": 5, "09": 5,
    "10": 5, "17": 5, "19": 5, "22": 12, "30": 12,
    "39": 18, "84": 18, "85": 18, "87": 28, "99": 18,
}


class IndianAccountingReality:
    """Rules engine for Indian accounting messiness — never assume perfect records."""

    @classmethod
    def clean_ledger_name(cls, name: str) -> tuple[str, list[str]]:
        """Normalize ledger name variants (M/s, Pvt Ltd, etc.)."""
        notes: list[str] = []
        cleaned = name.strip()
        if cleaned != name:
            notes.append(f"Trimmed whitespace from '{name}'")

        for pattern, replacement in LEDGER_PREFIX_VARIANTS:
            new = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            if new != cleaned:
                notes.append(f"Removed prefix variant: '{cleaned}' → '{new}'")
                cleaned = new.strip()

        for pattern, replacement in LEDGER_SUFFIX_VARIANTS:
            new = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            if new != cleaned:
                notes.append(f"Normalized suffix: '{cleaned}' → '{new}'")
                cleaned = new.strip()

        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned, notes

    @classmethod
    def clean_item_name(cls, name: str) -> tuple[str, list[str]]:
        notes: list[str] = []
        cleaned = name.strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned.lower() != name.lower().strip():
            notes.append(f"Normalized item name spacing/case")
        return cleaned, notes

    @classmethod
    def normalize_voucher_type(cls, voucher_type: str) -> tuple[str, list[str]]:
        notes: list[str] = []
        normalized = voucher_type.strip().lower()
        if normalized in VOUCHER_TYPE_ALIASES:
            canonical = VOUCHER_TYPE_ALIASES[normalized]
            notes.append(f"Mapped non-standard voucher type '{voucher_type}' → '{canonical}'")
            return canonical, notes
        return normalized, notes

    @classmethod
    def infer_gst_rate_from_hsn(cls, hsn_code: str | None) -> float | None:
        if not hsn_code or len(hsn_code) < 2:
            return None
        return HSN_GST_HINTS.get(hsn_code[:2])

    @classmethod
    def validate_gst_rate(cls, rate: float | None) -> tuple[bool, str | None]:
        if rate is None:
            return False, "GST rate missing"
        if rate not in VALID_GST_RATES:
            closest = min(VALID_GST_RATES, key=lambda r: abs(r - rate))
            return False, f"Non-standard GST rate {rate}% — nearest standard is {closest}%"
        return True, None

    @classmethod
    def validate_hsn(cls, hsn_code: str | None) -> tuple[bool, str | None]:
        if not hsn_code:
            return False, "HSN/SAC code missing"
        if not re.match(r"^\d{4,8}$", hsn_code):
            return False, f"Invalid HSN format: '{hsn_code}'"
        return True, None

    @classmethod
    def validate_gstin(cls, gstin: str | None) -> tuple[bool, str | None]:
        if not gstin:
            return False, "GSTIN missing"
        if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gstin.upper()):
            return False, f"Invalid GSTIN format: '{gstin}'"
        return True, None

    @classmethod
    def apply_ledger_rules(cls, obj: NormalizedLedger, aliases: dict[str, str] | None = None) -> None:
        name = obj.normalized_fields.get("name", "")
        cleaned, notes = cls.clean_ledger_name(name)
        for note in notes:
            obj.add_note(note)
        if cleaned != name:
            obj.normalized_fields["original_name"] = name
            obj.normalized_fields["name"] = cleaned

        if aliases:
            norm_key = cleaned.lower().strip()
            if norm_key in aliases:
                canonical = aliases[norm_key]
                obj.add_note(f"Resolved alias '{cleaned}' → '{canonical}'")
                obj.normalized_fields["name"] = canonical

        parent = obj.normalized_fields.get("parent_group") or ""
        if not parent:
            obj.add_issue("missing_parent_group", "Ledger has no parent group", IssueSeverity.WARNING,
                          "parent_group", "Assign to appropriate group (Sundry Debtors, etc.)")

        gstin = obj.normalized_fields.get("gstin")
        if gstin:
            valid, msg = cls.validate_gstin(gstin)
            if not valid:
                obj.add_issue("invalid_gstin", msg or "Invalid GSTIN", IssueSeverity.ERROR, "gstin",
                              "Verify GSTIN from party's registration certificate")
        elif parent and any(k in parent.lower() for k in ("debtor", "creditor", "vendor", "customer")):
            obj.add_issue("missing_gstin", "Party ledger missing GSTIN", IssueSeverity.WARNING, "gstin",
                          "Obtain GSTIN from party for compliance")

    @classmethod
    def apply_item_rules(cls, obj: NormalizedStockItem) -> None:
        name = obj.normalized_fields.get("name", "")
        cleaned, notes = cls.clean_item_name(name)
        for note in notes:
            obj.add_note(note)
        if cleaned != name:
            obj.normalized_fields["original_name"] = name
            obj.normalized_fields["name"] = cleaned

        hsn = obj.normalized_fields.get("hsn_code")
        gst_rate = obj.normalized_fields.get("gst_rate")

        hsn_valid, hsn_msg = cls.validate_hsn(hsn)
        if not hsn_valid:
            obj.add_issue("missing_or_invalid_hsn", hsn_msg or "HSN missing", IssueSeverity.WARNING,
                          "hsn_code", "Look up HSN on GST portal or from supplier invoice")

        if gst_rate is None and hsn:
            inferred = cls.infer_gst_rate_from_hsn(hsn)
            if inferred is not None:
                obj.normalized_fields["gst_rate"] = inferred
                obj.normalized_fields["gst_rate_inferred"] = True
                obj.add_note(f"Inferred GST rate {inferred}% from HSN chapter {hsn[:2]}")
        elif gst_rate is not None:
            valid, msg = cls.validate_gst_rate(gst_rate)
            if not valid:
                obj.add_issue("non_standard_gst_rate", msg or "Non-standard rate", IssueSeverity.WARNING,
                              "gst_rate", "Verify rate against GST schedule")

        if not obj.normalized_fields.get("unit"):
            obj.normalized_fields["unit"] = "NOS"
            obj.add_note("Defaulted missing unit to NOS")

    @classmethod
    def apply_voucher_rules(cls, obj: NormalizedVoucher) -> None:
        vch_type = obj.normalized_fields.get("voucher_type", "")
        canonical, notes = cls.normalize_voucher_type(vch_type)
        for note in notes:
            obj.add_note(note)
        obj.normalized_fields["voucher_type"] = canonical

        if canonical not in ("purchase", "sales", "receipt", "payment", "journal", "contra",
                             "debit_note", "credit_note", "expense"):
            obj.add_issue("non_standard_voucher_type", f"Unrecognized voucher type: '{vch_type}'",
                          IssueSeverity.WARNING, "voucher_type",
                          "Map to standard type for reporting")

        vch_date = obj.normalized_fields.get("voucher_date")
        if not vch_date:
            obj.add_issue("missing_voucher_date", "Voucher date missing", IssueSeverity.ERROR,
                          "voucher_date", "Set date from source document")
        elif isinstance(vch_date, str):
            try:
                obj.normalized_fields["voucher_date"] = date.fromisoformat(vch_date[:10])
            except ValueError:
                obj.add_issue("invalid_voucher_date", f"Cannot parse date: '{vch_date}'",
                              IssueSeverity.ERROR, "voucher_date")

        total = obj.normalized_fields.get("total_amount", 0)
        if total <= 0:
            obj.add_issue("zero_amount", "Voucher has zero or negative total", IssueSeverity.WARNING,
                          "total_amount")

        party_gstin = obj.normalized_fields.get("party_gstin")
        if party_gstin:
            valid, msg = cls.validate_gstin(party_gstin)
            if not valid:
                obj.add_issue("invalid_party_gstin", msg or "Invalid party GSTIN", IssueSeverity.ERROR,
                              "party_gstin")

        for line in obj.lines:
            cls._apply_voucher_line_rules(line)

    @classmethod
    def _apply_voucher_line_rules(cls, line: TwinObjectBase) -> None:
        hsn = line.normalized_fields.get("hsn_code")
        if hsn:
            valid, msg = cls.validate_hsn(hsn)
            if not valid:
                line.add_issue("invalid_line_hsn", msg or "Invalid HSN", IssueSeverity.WARNING, "hsn_code")

    @classmethod
    def apply_party_rules(cls, obj: NormalizedParty) -> None:
        name = obj.normalized_fields.get("name", "")
        cleaned, notes = cls.clean_ledger_name(name)
        for note in notes:
            obj.add_note(note)
        if cleaned != name:
            obj.normalized_fields["original_name"] = name
            obj.normalized_fields["name"] = cleaned

        gstin = obj.normalized_fields.get("gstin")
        if gstin:
            valid, msg = cls.validate_gstin(gstin)
            if not valid:
                obj.add_issue("invalid_gstin", msg or "Invalid GSTIN", IssueSeverity.ERROR, "gstin")
        else:
            obj.add_issue("missing_gstin", "Party missing GSTIN", IssueSeverity.INFO, "gstin",
                          "Obtain GSTIN if party is registered")

    @classmethod
    def detect_partial_fy_data(
        cls,
        vouchers: list[NormalizedVoucher],
        expected_fy_start: date | None = None,
    ) -> list[dict[str, Any]]:
        """Flag partial financial year data — common in mid-year imports."""
        warnings: list[dict[str, Any]] = []
        if not vouchers:
            return warnings

        dates: list[date] = []
        for v in vouchers:
            vd = v.normalized_fields.get("voucher_date")
            if isinstance(vd, date):
                dates.append(vd)
            elif isinstance(vd, str):
                try:
                    dates.append(date.fromisoformat(vd[:10]))
                except ValueError:
                    pass

        if not dates:
            warnings.append({
                "code": "no_dated_vouchers",
                "message": "No vouchers with valid dates — cannot assess FY completeness",
                "severity": "warning",
            })
            return warnings

        min_date, max_date = min(dates), max(dates)
        span_days = (max_date - min_date).days

        if span_days < 30:
            warnings.append({
                "code": "partial_fy_data",
                "message": f"Voucher span is only {span_days} days ({min_date} to {max_date})",
                "severity": "warning",
                "suggestion": "Import full FY data for accurate GST liability and outstanding reports",
            })

        if expected_fy_start and min_date > expected_fy_start:
            gap = (min_date - expected_fy_start).days
            if gap > 7:
                warnings.append({
                    "code": "fy_start_gap",
                    "message": f"Data starts {gap} days after FY start ({expected_fy_start})",
                    "severity": "info",
                    "suggestion": "Earlier period vouchers may be missing",
                })

        return warnings

    @classmethod
    def compute_quality_score(cls, obj: TwinObjectBase) -> float:
        """Score data quality 0-100 based on issues and completeness."""
        score = 100.0
        for issue in obj.issues:
            if issue.severity == IssueSeverity.ERROR:
                score -= 20
            elif issue.severity == IssueSeverity.WARNING:
                score -= 8
            else:
                score -= 3

        fields = obj.normalized_fields
        if obj.object_type.value == "ledger":
            if not fields.get("parent_group"):
                score -= 5
            if not fields.get("name"):
                score -= 15
        elif obj.object_type.value == "stock_item":
            if not fields.get("hsn_code"):
                score -= 10
            if fields.get("gst_rate") is None:
                score -= 10
        elif obj.object_type.value == "voucher":
            if not fields.get("voucher_date"):
                score -= 15
            if fields.get("total_amount", 0) <= 0:
                score -= 10

        return max(0.0, min(100.0, score))
