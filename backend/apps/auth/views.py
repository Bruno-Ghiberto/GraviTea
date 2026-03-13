"""
Authentication views for Gravitea ERP.

Provides JWT token endpoints and user/role management.

Security Features:
- Progressive rate limiting on login (5/10/20 attempts -> 5min/30min/lock)
- Account lockout after excessive failed attempts
- Comprehensive security event logging
"""

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.managers.tenant_bound import get_current_tenant_id
from apps.core.models import Branch
from apps.core.observability.business_metrics import (
    record_auth_attempt,
    record_auth_failure,
    record_auth_success,
)
from apps.core.security.rate_limiter import LockoutTier, get_login_limiter

from .jwt import CustomTokenObtainPairSerializer
from .models import Role
from .schema import (
    branch_viewset_schema,
    logout_schema,
    role_viewset_schema,
    token_obtain_schema,
    user_viewset_schema,
)
from .serializers import (BranchSerializer, ChangePasswordSerializer,
                          RoleCreateSerializer, RoleSerializer,
                          UserCreateSerializer, UserSerializer,
                          UserUpdateSerializer)

logger = logging.getLogger("security")
User = get_user_model()


def _get_client_ip(request) -> str:
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@token_obtain_schema
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view with tenant context and rate limiting.

    POST /api/v1/auth/token/

    Security:
        - Rate limiting: 5 attempts -> 5min, 10 -> 30min, 20 -> account lock
        - Security logging on all attempts
        - IP and email tracking for brute-force detection
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").lower()
        ip_address = _get_client_ip(request)
        limiter = get_login_limiter()

        # Get tenant_id for metrics (may not exist for login attempts)
        tenant_id = str(request.user.tenant_id) if hasattr(request.user, "tenant_id") and request.user.tenant_id else "unknown"

        # Record auth attempt metric
        record_auth_attempt(tenant_id=tenant_id, method="pwd")

        # Check rate limiting before attempting authentication
        if limiter.is_blocked(email, ip_address):
            remaining = limiter.get_remaining_lockout_time(email, ip_address)
            status_info = limiter.get_status(email, ip_address)

            # Determine response message based on lockout tier
            if status_info.get("account_locked"):
                error_msg = "Account locked due to excessive failed attempts. Contact administrator."
            else:
                minutes = (remaining // 60) + 1
                error_msg = f"Too many failed login attempts. Try again in {minutes} minute(s)."

            logger.warning(
                f"Blocked login attempt: {email}",
                extra={
                    "email": email,
                    "ip": ip_address,
                    "remaining_seconds": remaining,
                    "account_locked": status_info.get("account_locked"),
                },
            )

            # Record auth failure metric for rate-limited attempt
            record_auth_failure(tenant_id=tenant_id, reason="rate_limited")

            response = Response(
                {
                    "detail": error_msg,
                    "retry_after": remaining,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(remaining)
            return response

        # Attempt authentication - SimpleJWT raises AuthenticationFailed on invalid credentials
        try:
            response = super().post(request, *args, **kwargs)

            # Success - clear rate limiting
            limiter.clear(email, ip_address)
            logger.info(
                f"Successful login: {email}",
                extra={"email": email, "ip": ip_address},
            )

            # Record auth success metric
            record_auth_success(tenant_id=tenant_id, method="pwd")
            return response

        except AuthenticationFailed as exc:
            # Record failed attempt - this is the critical fix
            # SimpleJWT raises AuthenticationFailed instead of returning non-200 response
            tier = limiter.record_failure(email, ip_address)

            logger.warning(
                f"Failed login attempt: {email}",
                extra={
                    "email": email,
                    "ip": ip_address,
                    "tier": tier.value,
                },
            )

            # Record auth failure metric
            record_auth_failure(tenant_id=tenant_id, reason="invalid_creds")

            # Check if this failure triggered a lockout
            if tier != LockoutTier.NONE:
                status_info = limiter.get_status(email, ip_address)
                remaining = status_info.get("remaining_lockout_seconds", 0)

                # Return 429 immediately if locked out
                if limiter.is_blocked(email, ip_address):
                    if tier == LockoutTier.TIER_3:
                        error_msg = "Account locked due to excessive failed attempts. Contact administrator."
                    else:
                        minutes = (remaining // 60) + 1
                        error_msg = f"Too many failed login attempts. Try again in {minutes} minute(s)."

                    response = Response(
                        {
                            "detail": error_msg,
                            "retry_after": remaining,
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )
                    response["Retry-After"] = str(remaining)
                    return response

            # Not locked out yet - re-raise the exception (will return 401)
            raise


@logout_schema
class LogoutView(APIView):
    """
    Logout and blacklist the refresh token.

    POST /api/v1/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(f"User logged out: {request.user.email}")

            return Response(status=status.HTTP_205_RESET_CONTENT)

        except Exception as e:
            logger.warning(f"Logout failed: {e}")
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


@user_viewset_schema
class UserViewSet(viewsets.ModelViewSet):
    """
    User management viewset.

    Endpoints:
        GET    /api/v1/auth/users/           - List users in tenant
        POST   /api/v1/auth/users/           - Create user
        GET    /api/v1/auth/users/{id}/      - Get user details
        PATCH  /api/v1/auth/users/{id}/      - Update user
        DELETE /api/v1/auth/users/{id}/      - Deactivate user (soft delete)
        GET    /api/v1/auth/users/me/        - Get current user
        PATCH  /api/v1/auth/users/me/        - Update current user
        POST   /api/v1/auth/users/me/change-password/ - Change password
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return users for current tenant."""
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Tenant context not set")
        return User.objects.filter(tenant_id=tenant_id).select_related("role", "default_branch")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        """Soft delete user by deactivating."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        logger.info(f"User deactivated: {instance.email}")

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        """Get or update current user profile."""
        if request.method == "GET":
            serializer = UserSerializer(request.user)
            return Response(serializer.data)

        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="me/change-password")
    def change_password(self, request):
        """Change current user's password."""
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": ["Current password is incorrect."]})

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        logger.info(f"Password changed: {user.email}")

        return Response({"detail": "Password changed successfully."})


@role_viewset_schema
class RoleViewSet(viewsets.ModelViewSet):
    """
    Role management viewset.

    Endpoints:
        GET    /api/v1/auth/roles/      - List roles in tenant
        POST   /api/v1/auth/roles/      - Create role
        GET    /api/v1/auth/roles/{id}/ - Get role details
        PATCH  /api/v1/auth/roles/{id}/ - Update role
        DELETE /api/v1/auth/roles/{id}/ - Delete role
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return roles for current tenant."""
        return Role.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return RoleCreateSerializer
        return RoleSerializer

    def perform_destroy(self, instance):
        """Delete role if not assigned to users."""
        if instance.users.exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "Cannot delete role assigned to users."})
        instance.delete()


@branch_viewset_schema
class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Branch read-only viewset.

    Endpoints:
        GET /api/v1/auth/branches/      - List branches in tenant
        GET /api/v1/auth/branches/{id}/ - Get branch details
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BranchSerializer

    def get_queryset(self):
        """Return branches for current tenant."""
        return Branch.objects.filter(is_active=True)
