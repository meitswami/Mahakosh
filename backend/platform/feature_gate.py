"""Feature gating — enable/disable capabilities based on subscription plan."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.platform import FeatureFlag, Subscription
from backend.platform.plans import get_plan, plan_has_feature


class FeatureGate:
    FEATURES = (
        "ocr", "agents", "tally", "workflows", "whatsapp", "telegram",
        "forecasting", "advanced_reporting", "white_label", "partner_mode", "sso", "api_access",
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_effective_features(self, tenant_id: UUID) -> dict[str, bool]:
        plan_tier = await self._get_plan_tier(tenant_id)
        plan_features = get_plan(plan_tier).get("features", {})

        overrides = await self.db.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant_id,
                FeatureFlag.is_active.is_(True),
            )
        )
        effective = dict(plan_features)
        for flag in overrides.scalars().all():
            effective[flag.feature_key] = flag.enabled
        return effective

    async def is_enabled(self, tenant_id: UUID, feature: str) -> bool:
        features = await self.get_effective_features(tenant_id)
        return features.get(feature, False)

    async def require_feature(self, tenant_id: UUID, feature: str) -> None:
        if not await self.is_enabled(tenant_id, feature):
            plan_tier = await self._get_plan_tier(tenant_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' is not available on your {plan_tier} plan. Upgrade to unlock.",
            )

    async def _get_plan_tier(self, tenant_id: UUID) -> str:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(["active", "trial"]),
            ).order_by(Subscription.created_at.desc()).limit(1)
        )
        sub = result.scalar_one_or_none()
        if sub:
            return sub.plan_tier
        from backend.models.tenant import Tenant
        tenant = await self.db.get(Tenant, tenant_id)
        return tenant.subscription_tier if tenant else "starter"


def require_feature(feature: str):
    from typing import Annotated
    from fastapi import Depends
    from backend.core.database import get_db
    from backend.core.dependencies import CurrentUser, get_current_user

    async def checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> CurrentUser:
        gate = FeatureGate(db)
        await gate.require_feature(current_user.tenant_id, feature)
        return current_user

    return checker
