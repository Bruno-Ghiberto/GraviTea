"""
Custom DRF authentication that sets tenant context after JWT validation.

SECURITY: This is critical for multi-tenant isolation. The tenant context
must be set AFTER DRF authentication validates the JWT, not in Django middleware.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.managers.tenant_bound import (clear_current_tenant_id,
                                             set_current_tenant_id)


class TenantAwareJWTAuthentication(JWTAuthentication):
    """
    JWT authentication that extracts and sets tenant context.

    This extends SimpleJWT's authentication to:
    1. Validate the JWT token (via parent class)
    2. Extract tenant_id from JWT claims
    3. Set the tenant context for ORM filtering

    IMPORTANT: Use this instead of JWTAuthentication in REST_FRAMEWORK settings.
    """

    def authenticate(self, request):
        """
        Authenticate request and set tenant context.

        Returns:
            Tuple of (user, token) if authenticated, None otherwise.
        """
        result = super().authenticate(request)

        if result is None:
            # Not authenticated - clear any existing context
            clear_current_tenant_id()
            return None

        user, validated_token = result

        # Extract tenant_id from user (primary) or token claims (fallback)
        tenant_id = getattr(user, "tenant_id", None)

        if tenant_id is None:
            # Fallback: try to get from token claims
            tenant_id_str = validated_token.get("tenant_id")
            if tenant_id_str:
                from uuid import UUID

                try:
                    tenant_id = UUID(tenant_id_str)
                except ValueError:
                    tenant_id = None

        # Set tenant context for ORM filtering
        if tenant_id:
            set_current_tenant_id(tenant_id)

        # Attach tenant_id to request for convenience
        request.tenant_id = tenant_id
        request.branch_id = getattr(user, "default_branch_id", None)

        return result
