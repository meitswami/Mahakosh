from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant context from JWT or X-Tenant-ID header for downstream use."""

    EXEMPT_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json", "/api/v1/auth/login", "/api/v1/auth/register"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.tenant_id = None

        if request.url.path not in self.EXEMPT_PATHS and not request.url.path.startswith("/api/v1/auth/refresh"):
            tenant_header = request.headers.get("X-Tenant-ID")
            if tenant_header:
                request.state.tenant_id = tenant_header

        return await call_next(request)
