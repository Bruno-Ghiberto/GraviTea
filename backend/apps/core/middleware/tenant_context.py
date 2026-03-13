"""
Tenant context middleware for multi-tenant isolation.

Extracts tenant_id from JWT claims and sets both Python context
and PostgreSQL session variable for defense-in-depth tenant isolation.

SECURITY: This middleware is CRITICAL for tenant data isolation.
It sets context for both:
1. TenantBoundManager (ORM-level filtering)
2. PostgreSQL RLS policies (database-level filtering)
"""

import logging
from uuid import UUID

from django.http import JsonResponse

from apps.core.managers.tenant_bound import (clear_tenant_context,
                                             set_current_tenant_id)

logger = logging.getLogger("security")


def _get_security_logger():
    """Lazy import of SecurityLogger to avoid circular imports."""
    try:
        from apps.core.security.logging import SecurityLogger

        return SecurityLogger
    except ImportError:
        return None


class TenantContextMiddleware:
    """
    Middleware that extracts tenant_id from JWT and sets tenant context.

    This middleware:
    1. Extracts tenant_id from JWT claims (set by SimpleJWT authentication)
    2. Sets Python contextvars for TenantBoundManager ORM filtering
    3. Sets PostgreSQL session variable (app.current_tenant_id) for RLS
    4. Attaches tenant_id and branch_id to the request object
    5. Clears all context after request processing

    SECURITY: Both Python and PostgreSQL context must be set for
    defense-in-depth tenant isolation per FR-001, FR-002, FR-003.
    """

    # Paths that don't require tenant context
    EXEMPT_PATHS = [
        "/health/",
        "/api/v1/auth/token/",
        "/admin/",
        "/static/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip tenant context for exempt paths
        if self._is_exempt_path(request.path):
            return self.get_response(request)

        tenant_id = None
        branch_id = None

        # Try to extract from authenticated user (set by JWT authentication)
        if hasattr(request, "user") and request.user.is_authenticated:
            tenant_id = getattr(request.user, "tenant_id", None)
            branch_id = getattr(request.user, "default_branch_id", None)

        # Also check JWT claims directly (for API requests before user is loaded)
        if tenant_id is None and hasattr(request, "auth") and request.auth:
            try:
                tenant_id_str = request.auth.get("tenant_id")
                if tenant_id_str:
                    tenant_id = UUID(tenant_id_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid tenant_id in JWT: {e}")

            try:
                branch_id_str = request.auth.get("branch_id")
                if branch_id_str:
                    branch_id = UUID(branch_id_str)
            except (ValueError, TypeError):
                pass  # branch_id is optional

        # Set tenant context (both Python contextvars AND PostgreSQL session)
        # CRITICAL: This enables both ORM filtering AND RLS policies
        set_current_tenant_id(tenant_id)

        # Log tenant context set using structured security logger
        sec_logger = _get_security_logger()
        if sec_logger and tenant_id:
            user_id = getattr(request.user, "id", None) if hasattr(request, "user") else None
            sec_logger.tenant_context_set(
                tenant_id=tenant_id,
                source="middleware",
                user_id=user_id,
                request_path=request.path,
            )

        # Attach to request for convenience
        request.tenant_id = tenant_id
        request.branch_id = branch_id

        try:
            response = self.get_response(request)
        finally:
            # Always clear context after request (both Python and PostgreSQL)
            clear_tenant_context()
            if sec_logger:
                sec_logger.tenant_context_clear(source="middleware")

        return response

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from tenant context requirement."""
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False

    def process_exception(self, request, exception):
        """
        Handle tenant context errors gracefully.

        If a ValueError is raised due to missing tenant context,
        return a proper 401/403 response instead of 500.
        """
        if isinstance(exception, ValueError):
            if "Tenant context not set" in str(exception):
                logger.warning(f"Tenant context missing for {request.path}")
                return JsonResponse(
                    {"detail": "Authentication required. Please provide a valid JWT token."},
                    status=401,
                )
        return None
