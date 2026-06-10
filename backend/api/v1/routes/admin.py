from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.dependencies import require_role
from backend.core.security import UserRole
from backend.connectors.registry import connector_registry

import backend.connectors.mcp.tally  # noqa: F401 — register connectors

router = APIRouter()


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    password: str


class TenantSettingsUpdate(BaseModel):
    settings: dict


@router.get("/users")
async def list_users(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {"users": [], "total": 0}


@router.post("/users", status_code=201)
async def create_user(
    request: UserCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {"status": "ready", "email": request.email, "role": request.role.value}


@router.get("/roles")
async def list_roles(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {
        "roles": [
            {"name": role.value, "level": idx}
            for idx, role in enumerate(
                [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT, UserRole.AUDITOR, UserRole.VIEWER],
                1,
            )
        ]
    }


@router.get("/settings")
async def get_settings(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {"settings": {}, "tenant_id": str(current_user.tenant_id)}


@router.put("/settings")
async def update_settings(
    request: TenantSettingsUpdate,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {"status": "updated", "settings": request.settings}


@router.get("/connectors")
async def list_connectors(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {"connectors": connector_registry.list_connectors()}


@router.get("/system/health")
async def system_health(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    return {
        "status": "healthy",
        "services": {
            "api": "up",
            "database": "up",
            "redis": "up",
            "qdrant": "up",
            "minio": "up",
            "temporal": "up",
            "ollama": "up",
        },
    }
