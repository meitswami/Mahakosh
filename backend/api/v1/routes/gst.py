from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.dependencies import require_role
from backend.core.security import UserRole

router = APIRouter()


class GSTINValidationRequest(BaseModel):
    gstin: str = Field(min_length=15, max_length=15, pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


class GSTINValidationResponse(BaseModel):
    gstin: str
    status: str
    legal_name: str | None = None
    trade_name: str | None = None
    taxpayer_type: str | None = None


class HSNLookupRequest(BaseModel):
    hsn_code: str = Field(min_length=4, max_length=10)
    description: str | None = None


@router.post("/validate", response_model=GSTINValidationResponse)
async def validate_gstin(
    request: GSTINValidationRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
) -> GSTINValidationResponse:
    return GSTINValidationResponse(gstin=request.gstin, status="ready")


@router.post("/hsn/lookup")
async def lookup_hsn(
    request: HSNLookupRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {"hsn_code": request.hsn_code, "mappings": [], "status": "ready"}


@router.get("/validations")
async def list_gst_validations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return {"validations": [], "total": 0}
