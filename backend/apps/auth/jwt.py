"""
Custom JWT token serializers for Gravitea ERP.

Adds tenant_id and branch_id claims to JWT tokens for
multi-tenant context propagation per research.md.
"""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that adds tenant context to JWT.

    Adds the following claims to the access token:
    - tenant_id: UUID of the user's tenant
    - branch_id: UUID of user's default branch (or null)

    These claims are extracted by TenantContextMiddleware to set
    the tenant context for each request.
    """

    @classmethod
    def get_token(cls, user):
        """
        Generate token with custom claims.

        Args:
            user: AppUser instance.

        Returns:
            Token with tenant_id and branch_id claims.
        """
        token = super().get_token(user)

        # Add tenant context claims
        token["tenant_id"] = str(user.tenant_id)
        token["branch_id"] = str(user.default_branch_id) if user.default_branch_id else None

        # Add user info for frontend convenience
        token["email"] = user.email
        token["full_name"] = user.full_name or user.email

        return token

    def validate(self, attrs):
        """
        Validate credentials and return token data.

        Also checks:
        - User account is active
        - Tenant is active and subscription is valid
        """
        data = super().validate(attrs)

        # Check tenant status
        if not self.user.tenant.is_active:
            from rest_framework import exceptions

            raise exceptions.AuthenticationFailed(
                "Tenant account is suspended. Please contact support."
            )

        if not self.user.tenant.is_subscription_valid:
            from rest_framework import exceptions

            raise exceptions.AuthenticationFailed(
                "Subscription has expired. Please renew your plan."
            )

        # Add expiration info for frontend
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.user)
        data["access_expires_at"] = refresh.access_token.payload.get("exp")

        return data
