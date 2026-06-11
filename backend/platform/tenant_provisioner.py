"""Tenant provisioning — auto-provision workspace, admin, storage, settings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import UserRole, hash_password
from backend.models.platform import (
    License,
    Subscription,
    TenantBranding,
    TenantSetting,
)
from backend.models.role import Role
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.platform.plans import BillingCycle, PlanTier, get_plan
from backend.core.default_roles import DEFAULT_ROLES

logger = structlog.get_logger(__name__)


class TenantProvisioner:
    """
    New Customer → Auto Provision Tenant → Workspace → Admin → Storage → Settings
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def provision(
        self,
        *,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str,
        admin_full_name: str,
        tenant_type: str = "sme",
        plan_tier: str = PlanTier.STARTER,
        billing_cycle: str = BillingCycle.MONTHLY,
        created_by: UUID | None = None,
        trial_days: int = 14,
        branding: dict | None = None,
    ) -> dict:
        existing = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Tenant slug '{slug}' already exists")

        tenant = Tenant(
            name=name,
            slug=slug,
            display_name=name,
            tenant_type=tenant_type,
            subscription_tier=plan_tier,
            trial_ends_at=datetime.now(UTC) + timedelta(days=trial_days),
            is_active=True,
            settings={"provisioned_at": datetime.now(UTC).isoformat()},
        )
        self.db.add(tenant)
        await self.db.flush()

        roles = await self._seed_roles(tenant.id)
        admin_user = User(
            tenant_id=tenant.id,
            email=admin_email,
            hashed_password=hash_password(admin_password),
            full_name=admin_full_name,
            role_id=roles[UserRole.ADMIN].id,
            is_verified=True,
            is_active=True,
            created_by=created_by,
        )
        self.db.add(admin_user)
        await self.db.flush()

        subscription = await self._create_subscription(tenant.id, plan_tier, billing_cycle, trial_days)
        license_record = await self._create_license(tenant.id, plan_tier, subscription.id)
        await self._create_default_settings(tenant.id, plan_tier)
        await self._create_branding(tenant.id, name, branding or {})
        await self._provision_storage(tenant.id)
        await self._provision_vector_store(tenant.id)

        logger.info("tenant_provisioned", tenant_id=str(tenant.id), slug=slug, plan=plan_tier)

        return {
            "tenant_id": str(tenant.id),
            "slug": tenant.slug,
            "admin_user_id": str(admin_user.id),
            "subscription_id": str(subscription.id),
            "license_id": str(license_record.id),
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        }

    async def _seed_roles(self, tenant_id: UUID) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for role_def in DEFAULT_ROLES:
            role = Role(
                tenant_id=tenant_id,
                name=role_def["name"],
                display_name=role_def["display_name"],
                permissions=role_def["permissions"],
                is_system=True,
            )
            self.db.add(role)
            roles[role_def["name"]] = role
        await self.db.flush()
        return roles

    async def _create_subscription(
        self,
        tenant_id: UUID,
        plan_tier: str,
        billing_cycle: str,
        trial_days: int,
    ) -> Subscription:
        plan = get_plan(plan_tier)
        now = datetime.now(UTC)
        period_end = now + timedelta(days=30 if billing_cycle == BillingCycle.MONTHLY else 365)

        sub = Subscription(
            tenant_id=tenant_id,
            plan_tier=plan_tier,
            billing_cycle=billing_cycle,
            status="trial" if trial_days > 0 else "active",
            price_inr=plan.get("price_monthly_inr", 0) if billing_cycle == BillingCycle.MONTHLY else plan.get("price_yearly_inr", 0),
            max_users=plan.get("max_users", 3),
            max_storage_gb=plan.get("max_storage_gb", 5),
            features=plan.get("features", {}),
            current_period_start=now,
            current_period_end=period_end,
            trial_ends_at=now + timedelta(days=trial_days) if trial_days > 0 else None,
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def _create_license(self, tenant_id: UUID, plan_tier: str, subscription_id: UUID) -> License:
        plan = get_plan(plan_tier)
        license_record = License(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            plan_tier=plan_tier,
            status="active",
            max_users=plan.get("max_users", 3),
            max_storage_gb=plan.get("max_storage_gb", 5),
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
        )
        self.db.add(license_record)
        await self.db.flush()
        return license_record

    async def _create_default_settings(self, tenant_id: UUID, plan_tier: str) -> None:
        defaults = [
            ("locale", "en-IN", "general"),
            ("timezone", "Asia/Kolkata", "general"),
            ("currency", "INR", "general"),
            ("fiscal_year_start", "04-01", "accounting"),
            ("plan_tier", plan_tier, "billing"),
            ("retention_days", "2555", "governance"),
            ("audit_enabled", "true", "governance"),
            ("approval_required_vouchers", "true", "governance"),
        ]
        for key, value, category in defaults:
            self.db.add(TenantSetting(
                tenant_id=tenant_id,
                setting_key=key,
                setting_value=value,
                category=category,
            ))
        await self.db.flush()

    async def _create_branding(self, tenant_id: UUID, name: str, branding: dict) -> TenantBranding:
        record = TenantBranding(
            tenant_id=tenant_id,
            logo_url=branding.get("logo_url"),
            favicon_url=branding.get("favicon_url"),
            primary_color=branding.get("primary_color", "#1a56db"),
            secondary_color=branding.get("secondary_color", "#7e3af2"),
            accent_color=branding.get("accent_color", "#0e9f6e"),
            custom_domain=branding.get("custom_domain"),
            login_title=branding.get("login_title", name),
            login_subtitle=branding.get("login_subtitle", "ज्ञान से निर्णय तक"),
            email_from_name=branding.get("email_from_name", name),
            report_header=branding.get("report_header", name),
            is_white_label=branding.get("is_white_label", False),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def _provision_storage(self, tenant_id: UUID) -> None:
        try:
            from backend.services.storage_service import StorageService
            storage = StorageService()
            prefix = f"{tenant_id}/"
            logger.info("storage_prefix_provisioned", tenant_id=str(tenant_id), prefix=prefix)
        except Exception as exc:
            logger.warning("storage_provision_skipped", error=str(exc))

    async def _provision_vector_store(self, tenant_id: UUID) -> None:
        try:
            from backend.core.config import settings
            from backend.services.knowledge.qdrant_service import QdrantService
            qdrant = QdrantService()
            qdrant.ensure_tenant_collections(str(tenant_id), settings.EMBEDDING_DIMENSION)
        except Exception as exc:
            logger.warning("qdrant_provision_skipped", error=str(exc))
