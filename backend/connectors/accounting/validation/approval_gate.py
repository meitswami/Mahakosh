"""Mandatory approval gate: Draft → Validation → Approval → Export."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from backend.connectors.accounting.validation.validation_engine import ValidationEngine


class VoucherPipelineStage(StrEnum):
    DRAFT = "draft"
    VALIDATION = "validation"
    APPROVAL = "approval"
    EXPORT = "export"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ApprovalGate:
    """Nothing exports directly — all exports must pass through this gate."""

    def __init__(self):
        self._validator = ValidationEngine()

    def process_draft(self, voucher: dict[str, Any]) -> dict[str, Any]:
        validation = self._validator.validate_voucher_draft(voucher)
        stage = VoucherPipelineStage.VALIDATION if validation["is_valid"] else VoucherPipelineStage.DRAFT
        return {
            "stage": stage.value,
            "validation": validation,
            "validation_status": validation["status"],
            "can_proceed_to_approval": validation["is_valid"],
            "export_allowed": False,
        }

    def process_approval(self, voucher: dict[str, Any], approval_status: str) -> dict[str, Any]:
        validation = self._validator.validate_voucher_draft(voucher)
        if not validation["is_valid"]:
            return {
                "stage": VoucherPipelineStage.VALIDATION.value,
                "validation": validation,
                "export_allowed": False,
                "reasoning": "Cannot approve — validation failed",
            }
        if approval_status == "approved":
            return {
                "stage": VoucherPipelineStage.EXPORT.value,
                "validation": validation,
                "approval_status": "approved",
                "export_allowed": True,
                "reasoning": "Approved — export permitted",
            }
        if approval_status == "rejected":
            return {
                "stage": VoucherPipelineStage.REJECTED.value,
                "validation": validation,
                "approval_status": "rejected",
                "export_allowed": False,
                "reasoning": "Rejected — export blocked",
            }
        return {
            "stage": VoucherPipelineStage.APPROVAL.value,
            "validation": validation,
            "approval_status": approval_status,
            "export_allowed": False,
            "reasoning": "Pending approval",
        }

    def can_export(self, voucher: dict[str, Any], validation_status: str, approval_status: str) -> dict[str, Any]:
        validation = self._validator.validate_voucher_draft(voucher)
        readiness = self._validator.validate_export_readiness(voucher, validation, approval_status)
        if not readiness["is_valid"]:
            return {
                "allowed": False,
                "stage": VoucherPipelineStage.APPROVAL.value if approval_status != "approved" else VoucherPipelineStage.VALIDATION.value,
                "readiness": readiness,
                "reasoning": readiness["reasoning"],
            }
        return {
            "allowed": True,
            "stage": VoucherPipelineStage.EXPORT.value,
            "readiness": readiness,
            "reasoning": "All gates passed — export authorized",
        }

    def enforce_export(
        self,
        voucher_id: UUID,
        voucher: dict[str, Any],
        validation_status: str,
        approval_status: str,
    ) -> dict[str, Any]:
        check = self.can_export(voucher, validation_status, approval_status)
        if not check["allowed"]:
            raise ExportBlockedError(
                f"Export blocked for voucher {voucher_id}: {check['reasoning']}",
                stage=check["stage"],
                readiness=check.get("readiness", {}),
            )
        return {"authorized": True, "voucher_id": str(voucher_id), "stage": VoucherPipelineStage.EXPORT.value}


class ExportBlockedError(Exception):
    def __init__(self, message: str, stage: str = "", readiness: dict | None = None):
        super().__init__(message)
        self.stage = stage
        self.readiness = readiness or {}
