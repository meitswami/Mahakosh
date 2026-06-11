from typing import Any

from pydantic import BaseModel, EmailStr, Field


class TenantCreateRequest(BaseModel):
    name: str
    slug: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_full_name: str
    tenant_type: str = "sme"
    plan_tier: str = "starter"
    billing_cycle: str = "monthly"
    branding: dict[str, Any] = Field(default_factory=dict)


class TenantBrandingUpdate(BaseModel):
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    custom_domain: str | None = None
    login_title: str | None = None
    login_subtitle: str | None = None
    email_from_name: str | None = None
    report_header: str | None = None
    report_footer: str | None = None
    is_white_label: bool | None = None


class LicenseCreateRequest(BaseModel):
    tenant_id: str
    plan_tier: str
    duration_days: int = 365


class FeatureFlagRequest(BaseModel):
    feature_key: str
    enabled: bool
    reason: str | None = None


class PartnerRegisterRequest(BaseModel):
    partner_type: str
    company_name: str
    contact_email: EmailStr
    max_clients: int = 50


class PartnerClientProvisionRequest(BaseModel):
    name: str
    slug: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_full_name: str
    plan_tier: str = "professional"
