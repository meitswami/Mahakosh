from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import (
    UserRole,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from backend.models.platform import Subscription
from backend.models.role import Role
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.platform.governance import GovernanceService
from backend.platform.tenant_provisioner import TenantProvisioner
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, request: RegisterRequest) -> tuple[User, Tenant, TokenResponse]:
        provisioner = TenantProvisioner(self.db)
        try:
            result = await provisioner.provision(
                name=request.tenant_name,
                slug=request.tenant_slug,
                admin_email=request.email,
                admin_password=request.password,
                admin_full_name=request.full_name,
                tenant_type="sme",
                plan_tier="starter",
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

        tenant_id = UUID(result["tenant_id"])
        user_id = UUID(result["admin_user_id"])
        await GovernanceService(self.db).seed_default_policies(tenant_id)

        tenant = await self.db.get(Tenant, tenant_id)
        user = await self.db.get(User, user_id)
        if user and request.phone:
            user.phone = request.phone
            await self.db.flush()

        tokens = self._create_tokens(user, tenant.id, UserRole.ADMIN)
        return user, tenant, tokens

    async def login(self, request: LoginRequest) -> tuple[User, TokenResponse]:
        query = select(User).join(Tenant).where(User.email == request.email, User.is_active.is_(True))

        if request.tenant_slug:
            query = query.where(Tenant.slug == request.tenant_slug)

        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if user is None or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

        tenant = await self.db.get(Tenant, user.tenant_id)
        if tenant is None or not tenant.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tenant account is inactive")

        sub_result = await self.db.execute(
            select(Subscription).where(
                Subscription.tenant_id == user.tenant_id,
                Subscription.status.in_(["active", "trial"]),
            ).order_by(Subscription.created_at.desc()).limit(1)
        )
        subscription = sub_result.scalar_one_or_none()
        now = datetime.now(UTC)
        if subscription is None and tenant.trial_ends_at and tenant.trial_ends_at < now:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Trial period has expired. Please upgrade your plan.")
        if subscription and subscription.status == "trial" and subscription.trial_ends_at and subscription.trial_ends_at < now:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Trial period has expired. Please upgrade your plan.")

        role_result = await self.db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one()

        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

        tokens = self._create_tokens(user, user.tenant_id, UserRole(role.name))
        return user, tokens

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        role_result = await self.db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one()

        return self._create_tokens(user, tenant_id, UserRole(role.name))

    async def get_user_response(self, user: User) -> UserResponse:
        role_result = await self.db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one()

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=role.name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_platform_admin=user.is_platform_admin,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url,
            tenant_id=user.tenant_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _create_tokens(self, user: User, tenant_id: UUID, role: UserRole) -> TokenResponse:
        from backend.core.config import settings

        access_token = create_access_token(user.id, tenant_id, role)
        refresh_token = create_refresh_token(user.id, tenant_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
