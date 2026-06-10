from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.dependencies import require_role
from backend.core.security import UserRole

router = APIRouter()


class ReportDefinition(BaseModel):
    name: str
    report_type: str
    parameters: dict = {}


class ReportResponse(BaseModel):
    id: UUID | None = None
    name: str
    report_type: str
    status: str


@router.get("")
async def list_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {"reports": [], "total": 0}


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    definition: ReportDefinition,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
) -> ReportResponse:
    return ReportResponse(
        name=definition.name,
        report_type=definition.report_type,
        status="ready",
    )


@router.get("/templates")
async def list_report_templates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {
        "templates": [
            {"type": "gst_summary", "name": "GST Summary Report"},
            {"type": "vendor_ledger", "name": "Vendor Ledger"},
            {"type": "purchase_register", "name": "Purchase Register"},
            {"type": "sales_register", "name": "Sales Register"},
            {"type": "itc_reconciliation", "name": "ITC Reconciliation"},
        ]
    }
