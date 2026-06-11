"""Platform service — tenant registry, subscriptions, super admin operations."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.platform import (
    BillingEvent,
    FeatureFlag,
    License,
    PartnerAccount,
    Subscription,
    TenantBranding,
    TenantSetting,
    UsageMetric,
)
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.platform.feature_gate import FeatureGate
from backend.platform.governance import GovernanceService
from backend.platform.partner_service import PartnerService
from backend.platform.plans import PLAN_DEFINITIONS, PlanTier, get_plan
from backend.platform.tenant_provisioner import TenantProvisioner
from backend.platform.usage_tracker import UsageTracker


class PlatformService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provisioner = TenantProvisioner(db)
        self.usage = UsageTracker(db)
        self.features = FeatureGate(db)
        self.governance = GovernanceService(db)
        self.partners = PartnerService(db)

    async def create_tenant(
        self,
        *,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str,
        admin_full_name: str,
        tenant_type: str = "sme",
        plan_tier: str = PlanTier.STARTER,
        billing_cycle: str = "monthly",
        created_by: UUID | None = None,
        branding: dict | None = None,
    ) -> dict:
        result = await self.provisioner.provision(
            name=name,
            slug=slug,
            admin_email=admin_email,
            admin_password=admin_password,
            admin_full_name=admin_full_name,
            tenant_type=tenant_type,
            plan_tier=plan_tier,
            billing_cycle=billing_cycle,
            created_by=created_by,
            branding=branding,
        )
        await self.governance.seed_default_policies(UUID(result["tenant_id"]))
        return result

    async def list_tenants(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        tenant_type: str | None = None,
        active_only: bool = True,
    ) -> dict:
        query = select(Tenant)
        if active_only:
            query = query.where(Tenant.is_active.is_(True))
        if tenant_type:
            query = query.where(Tenant.tenant_type == tenant_type)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        result = await self.db.execute(
            query.order_by(Tenant.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        tenants = []
        for t in result.scalars().all():
            user_count = (await self.db.execute(
                select(func.count()).select_from(User).where(User.tenant_id == t.id, User.is_active.is_(True))
            )).scalar() or 0
            tenants.append({
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "display_name": t.display_name,
                "tenant_type": t.tenant_type,
                "subscription_tier": t.subscription_tier,
                "is_active": t.is_active,
                "user_count": user_count,
                "trial_ends_at": t.trial_ends_at.isoformat() if t.trial_ends_at else None,
                "created_at": t.created_at.isoformat(),
            })
        return {"tenants": tenants, "total": total, "page": page, "page_size": page_size}

    async def get_tenant_detail(self, tenant_id: UUID) -> dict | None:
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant:
            return None

        sub_result = await self.db.execute(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
            .order_by(Subscription.created_at.desc()).limit(1)
        )
        sub = sub_result.scalar_one_or_none()

        branding_result = await self.db.execute(
            select(TenantBranding).where(TenantBranding.tenant_id == tenant_id)
        )
        branding = branding_result.scalar_one_or_none()

        usage = await self.usage.get_usage_summary(tenant_id)
        features = await self.features.get_effective_features(tenant_id)

        return {
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "tenant_type": tenant.tenant_type,
                "subscription_tier": tenant.subscription_tier,
                "is_active": tenant.is_active,
                "custom_domain": tenant.custom_domain,
            },
            "subscription": {
                "plan_tier": sub.plan_tier if sub else tenant.subscription_tier,
                "status": sub.status if sub else "unknown",
                "billing_cycle": sub.billing_cycle if sub else None,
                "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
            } if sub else None,
            "branding": {
                "logo_url": branding.logo_url if branding else None,
                "primary_color": branding.primary_color if branding else None,
                "is_white_label": branding.is_white_label if branding else False,
                "custom_domain": branding.custom_domain if branding else None,
            } if branding else None,
            "usage": usage,
            "features": features,
        }

    async def get_subscriptions(self, tenant_id: UUID | None = None) -> list[dict]:
        query = select(Subscription)
        if tenant_id:
            query = query.where(Subscription.tenant_id == tenant_id)
        result = await self.db.execute(query.order_by(Subscription.created_at.desc()).limit(100))
        return [
            {
                "id": str(s.id),
                "tenant_id": str(s.tenant_id),
                "plan_tier": s.plan_tier,
                "billing_cycle": s.billing_cycle,
                "status": s.status,
                "price_inr": s.price_inr,
                "max_users": s.max_users,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            }
            for s in result.scalars().all()
        ]

    async def create_license(self, tenant_id: UUID, plan_tier: str, duration_days: int = 365) -> dict:
        plan = get_plan(plan_tier)
        license_key = f"MK-{secrets.token_hex(8).upper()}-{plan_tier[:3].upper()}"
        record = License(
            tenant_id=tenant_id,
            plan_tier=plan_tier,
            license_key=license_key,
            status="active",
            max_users=plan.get("max_users", 3),
            max_storage_gb=plan.get("max_storage_gb", 5),
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=duration_days),
        )
        self.db.add(record)
        await self.db.flush()
        return {"license_id": str(record.id), "license_key": license_key, "expires_at": record.expires_at.isoformat()}

    async def get_usage(self, tenant_id: UUID, days: int = 30) -> dict:
        return await self.usage.get_usage_summary(tenant_id, days)

    async def set_feature_flag(
        self,
        tenant_id: UUID,
        feature_key: str,
        enabled: bool,
        set_by: UUID,
        reason: str | None = None,
    ) -> dict:
        existing = await self.db.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant_id,
                FeatureFlag.feature_key == feature_key,
            )
        )
        flag = existing.scalar_one_or_none()
        if flag:
            flag.enabled = enabled
            flag.set_by = set_by
            flag.reason = reason
        else:
            flag = FeatureFlag(
                tenant_id=tenant_id,
                feature_key=feature_key,
                enabled=enabled,
                set_by=set_by,
                reason=reason,
            )
            self.db.add(flag)
        await self.db.flush()
        return {"feature_key": feature_key, "enabled": enabled}

    async def get_platform_dashboard(self) -> dict:
        total_tenants = (await self.db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
        active_tenants = (await self.db.execute(
            select(func.count()).select_from(Tenant).where(Tenant.is_active.is_(True))
        )).scalar() or 0
        total_users = (await self.db.execute(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )).scalar() or 0

        type_breakdown = await self.db.execute(
            select(Tenant.tenant_type, func.count()).group_by(Tenant.tenant_type)
        )
        by_type = {row[0]: row[1] for row in type_breakdown.fetchall()}

        plan_breakdown = await self.db.execute(
            select(Tenant.subscription_tier, func.count()).group_by(Tenant.subscription_tier)
        )
        by_plan = {row[0]: row[1] for row in plan_breakdown.fetchall()}

        recent_usage = (await self.db.execute(
            select(UsageMetric.metric_type, func.sum(UsageMetric.quantity))
            .group_by(UsageMetric.metric_type)
        )).fetchall()

        partners = (await self.db.execute(
            select(func.count()).select_from(PartnerAccount).where(PartnerAccount.status == "active")
        )).scalar() or 0

        return {
            "tenants": {"total": total_tenants, "active": active_tenants, "by_type": by_type},
            "users": {"total": total_users},
            "subscriptions": {"by_plan": by_plan},
            "usage_aggregate": {row[0]: int(row[1]) for row in recent_usage},
            "partners": partners,
            "plans": list(PLAN_DEFINITIONS.keys()),
            "health": "operational",
        }

    async def update_branding(self, tenant_id: UUID, branding: dict) -> dict:
        result = await self.db.execute(
            select(TenantBranding).where(TenantBranding.tenant_id == tenant_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            record = TenantBranding(tenant_id=tenant_id)
            self.db.add(record)

        for key in ("logo_url", "favicon_url", "primary_color", "secondary_color", "accent_color",
                    "custom_domain", "login_title", "login_subtitle", "email_from_name",
                    "report_header", "report_footer", "is_white_label"):
            if key in branding:
                setattr(record, key, branding[key])

        tenant = await self.db.get(Tenant, tenant_id)
        if tenant and branding.get("custom_domain"):
            tenant.custom_domain = branding["custom_domain"]

        await self.db.flush()
        return {"status": "updated", "tenant_id": str(tenant_id)}

    async def record_billing_event(
        self,
        tenant_id: UUID,
        event_type: str,
        amount_inr: float,
        subscription_id: UUID | None = None,
        description: str | None = None,
    ) -> dict:
        event = BillingEvent(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            event_type=event_type,
            amount_inr=amount_inr,
            status="completed",
            description=description,
        )
        self.db.add(event)
        await self.db.flush()
        return {"event_id": str(event.id), "status": event.status}
