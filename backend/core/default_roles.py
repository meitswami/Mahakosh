from backend.core.security import UserRole

DEFAULT_ROLES: list[dict] = [
    {"name": UserRole.ADMIN, "display_name": "Administrator", "permissions": ["*"]},
    {"name": UserRole.MANAGER, "display_name": "Manager", "permissions": ["read", "write", "approve"]},
    {"name": UserRole.ACCOUNTANT, "display_name": "Accountant", "permissions": ["read", "write", "accounting"]},
    {"name": UserRole.VIEWER, "display_name": "Viewer", "permissions": ["read"]},
    {"name": UserRole.AUDITOR, "display_name": "Auditor", "permissions": ["read", "audit"]},
]
