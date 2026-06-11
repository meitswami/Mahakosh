from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from backend.schemas.common import TimestampSchema


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_slug: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    phone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(TimestampSchema):
    id: UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    is_verified: bool
    is_platform_admin: bool = False
    last_login_at: datetime | None
    avatar_url: str | None
    tenant_id: UUID


class TenantResponse(TimestampSchema):
    id: UUID
    name: str
    slug: str
    display_name: str
    gstin: str | None
    is_active: bool
    subscription_tier: str
