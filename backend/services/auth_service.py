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
    hash_password,
    verify_password,
)
from backend.models.role import Role
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


DEFAULT_ROLES: list[dict] = [
    {"name": UserRole.ADMIN, "display_name": "Administrator", "permissions": ["*"]},
    {"name": UserRole.MANAGER, "display_name": "Manager", "permissions": ["read", "write", "approve"]},
    {"name": UserRole.ACCOUNTANT, "display_name": "Accountant", "permissions": ["read", "write", "accounting"]},
    {"name": UserRole.VIEWER, "display_name": "Viewer", "permissions": ["read"]},
    {"name": UserRole.AUDITOR, "display_name": "Auditor", "permissions": ["read", "audit"]},
]


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, request: RegisterRequest) -> tuple[User, Tenant, TokenResponse]:
        existing = await self.db.execute(select(Tenant).where(Tenant.slug == request.tenant_slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Tenant slug already exists")

        tenant = Tenant(
            name=request.tenant_name,
            slug=request.tenant_slug,
            display_name=request.tenant_name,
        )
        self.db.add(tenant)
        await self.db.flush()

        roles: dict[str, Role] = {}
        for role_def in DEFAULT_ROLES:
            role = Role(
                tenant_id=tenant.id,
                name=role_def["name"],
                display_name=role_def["display_name"],
                permissions=role_def["permissions"],
                is_system=True,
            )
            self.db.add(role)
            roles[role_def["name"]] = role
        await self.db.flush()

        admin_role = roles[UserRole.ADMIN]
        user = User(
            tenant_id=tenant.id,
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            phone=request.phone,
            role_id=admin_role.id,
            is_verified=True,
        )
        self.db.add(user)
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
