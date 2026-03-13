"""
OpenAPI schema definitions for auth endpoints.

Provides drf-spectacular schema decorators following RFC 7807 Problem Details
for error responses and comprehensive documentation for all auth endpoints.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers, status

from apps.core.exceptions.serializers import (
    AccountLockedErrorSerializer,
    FieldErrorSerializer,
    ProblemDetailSerializer,
    RateLimitErrorSerializer,
    ValidationErrorSerializer,
)


# ============================================================================
# Success Response Schemas
# ============================================================================


class TokenResponseSerializer(serializers.Serializer):
    """JWT token pair response."""

    access = serializers.CharField(help_text="JWT access token (short-lived)")
    refresh = serializers.CharField(help_text="JWT refresh token (long-lived)")


class LogoutSuccessSerializer(serializers.Serializer):
    """Logout success response (empty with 205 status)."""

    pass


class PasswordChangeSuccessSerializer(serializers.Serializer):
    """Password change success response."""

    detail = serializers.CharField(
        default="Password changed successfully.",
        help_text="Success message",
    )


# ============================================================================
# Token Obtain (Login) Schema
# ============================================================================

token_obtain_schema = extend_schema_view(
    post=extend_schema(
        operation_id="auth_token_create",
        summary="Obtain JWT token pair",
        description="""
Authenticate user and receive JWT access/refresh token pair.

**Security Features:**
- Progressive rate limiting (5 attempts → 5min lockout, 10 → 30min, 20 → account lock)
- IP-based brute force protection
- Security event logging
- Account lockout after excessive failures

**Rate Limit Tiers:**
- Tier 1: 5 failed attempts → 5 minute lockout
- Tier 2: 10 failed attempts → 30 minute lockout
- Tier 3: 20 failed attempts → account locked (admin unlock required)

**Response Codes:**
- 200: Authentication successful, tokens returned
- 401: Invalid credentials
- 429: Rate limit exceeded (see retry_after)
        """,
        tags=["Authentication"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "User email address",
                        "example": "admin@gravitea-demo.com",
                    },
                    "password": {
                        "type": "string",
                        "format": "password",
                        "description": "User password",
                        "example": "admin123",
                    },
                },
                "required": ["email", "password"],
            }
        },
        responses={
            200: OpenApiResponse(
                response=TokenResponseSerializer,
                description="Authentication successful",
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Invalid credentials",
            ),
            429: OpenApiResponse(
                response=RateLimitErrorSerializer,
                description="Rate limit exceeded",
            ),
        },
    )
)


# ============================================================================
# Logout Schema
# ============================================================================

logout_schema = extend_schema_view(
    post=extend_schema(
        operation_id="auth_logout",
        summary="Logout and blacklist refresh token",
        description="""
Invalidate the provided refresh token by adding it to the blacklist.

**Request Body:**
- `refresh` (string, required): The JWT refresh token to blacklist

**Security:**
- Requires valid JWT access token in Authorization header
- Blacklisted tokens cannot be used to obtain new access tokens
- Security event logged

**Response Codes:**
- 205: Token successfully blacklisted (Reset Content)
- 400: Missing or invalid refresh token
- 401: Unauthorized (missing/invalid access token)
        """,
        tags=["Authentication"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "refresh": {
                        "type": "string",
                        "description": "JWT refresh token to blacklist",
                    }
                },
                "required": ["refresh"],
            }
        },
        responses={
            205: OpenApiResponse(
                response=LogoutSuccessSerializer,
                description="Token successfully blacklisted (no content)",
            ),
            400: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Missing or invalid refresh token",
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized - missing or invalid access token",
            ),
        },
    )
)


# ============================================================================
# User ViewSet Schemas
# ============================================================================

user_viewset_schema = extend_schema_view(
    list=extend_schema(
        operation_id="auth_users_list",
        summary="List users in tenant",
        description="""
Retrieve all users within the authenticated user's tenant/organization.

**Filters:**
- Results automatically scoped to current tenant
- Only active users shown by default

**Response:**
- Array of user objects with role and branch details
- Includes computed permissions from role

**Permissions:**
- Requires authentication
- Returns only users in same tenant
        """,
        tags=["User Management"],
        responses={
            200: OpenApiResponse(
                description="List of users retrieved successfully"
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized - authentication required",
            ),
        },
    ),
    retrieve=extend_schema(
        operation_id="auth_users_retrieve",
        summary="Get user details",
        description="""
Retrieve detailed information about a specific user.

**Returns:**
- User profile with role details
- Default branch information
- Computed permission list
- Activity timestamps

**Permissions:**
- Requires authentication
- User must be in same tenant
        """,
        tags=["User Management"],
        responses={
            200: OpenApiResponse(description="User details retrieved successfully"),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="User not found",
            ),
        },
    ),
    create=extend_schema(
        operation_id="auth_users_create",
        summary="Create new user",
        description="""
Create a new user in the current tenant/organization.

**Required Fields:**
- email: Valid email address (unique within tenant)
- full_name: User's full name
- password: Strong password (validated)

**Optional Fields:**
- role_id: UUID of role to assign (must be in same tenant)
- default_branch_id: UUID of default branch (must be in same tenant)

**Password Requirements:**
- Minimum 8 characters
- Cannot be entirely numeric
- Cannot be too similar to user information
- Cannot be a commonly used password

**Validation:**
- Email uniqueness checked within tenant
- Role/branch validated against tenant scope

**Permissions:**
- Requires authentication
- Creates user in same tenant as requester
        """,
        tags=["User Management"],
        responses={
            201: OpenApiResponse(description="User created successfully"),
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        name="Duplicate Email",
                        value={
                            "type": "about:blank",
                            "title": "Validation Error",
                            "status": 400,
                            "detail": "Request validation failed",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "errors": [
                                {
                                    "field": "email",
                                    "message": "A user with this email already exists in your organization.",
                                    "code": "unique",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        name="Weak Password",
                        value={
                            "type": "about:blank",
                            "title": "Validation Error",
                            "status": 400,
                            "detail": "Request validation failed",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "errors": [
                                {
                                    "field": "password",
                                    "message": "This password is too short. It must contain at least 8 characters.",
                                    "code": "password_too_short",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
        },
    ),
    partial_update=extend_schema(
        operation_id="auth_users_partial_update",
        summary="Update user",
        description="""
Partially update user profile information.

**Updatable Fields:**
- full_name: User's full name
- role_id: Assign different role (must be in same tenant)
- default_branch_id: Change default branch (must be in same tenant)
- is_active: Activate/deactivate user account

**Notes:**
- Password changes use separate endpoint: POST /me/change-password/
- Email cannot be changed after creation
- All fields optional for PATCH request

**Permissions:**
- Requires authentication
- User must be in same tenant
        """,
        tags=["User Management"],
        responses={
            200: OpenApiResponse(description="User updated successfully"),
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Validation error",
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="User not found",
            ),
        },
    ),
    destroy=extend_schema(
        operation_id="auth_users_destroy",
        summary="Deactivate user (soft delete)",
        description="""
Soft delete user by setting is_active=False.

**Behavior:**
- User account marked as inactive (not deleted from database)
- User cannot login after deactivation
- User data preserved for audit/history
- Can be reactivated by setting is_active=True

**Permissions:**
- Requires authentication
- User must be in same tenant

**Response:**
- 204: User deactivated successfully (no content)
        """,
        tags=["User Management"],
        responses={
            204: OpenApiResponse(description="User deactivated successfully"),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="User not found",
            ),
        },
    ),
    me=extend_schema(
        operation_id="auth_users_me",
        summary="Get/update current user profile",
        description="""
Retrieve or update the authenticated user's own profile.

**GET /api/v1/auth/users/me/**
Returns current user's profile with role, branch, and permissions.

**PATCH /api/v1/auth/users/me/**
Update current user's profile (same fields as PATCH /users/{id}/).

**Updatable Fields:**
- full_name
- default_branch_id (must be in same tenant)

**Restricted Fields:**
- Cannot change own role_id (requires admin)
- Cannot change own is_active status
- Use /me/change-password/ for password changes

**Permissions:**
- Requires authentication
- Always operates on authenticated user
        """,
        tags=["User Management"],
        responses={
            200: OpenApiResponse(description="Current user profile"),
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Validation error (PATCH only)",
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
        },
    ),
    change_password=extend_schema(
        operation_id="auth_users_change_password",
        summary="Change current user password",
        description="""
Change the authenticated user's password.

**Request Body:**
- current_password (string, required): Current password for verification
- new_password (string, required): New password (must meet strength requirements)

**Password Requirements:**
- Minimum 8 characters
- Cannot be entirely numeric
- Cannot be too similar to user information
- Cannot be a commonly used password

**Security:**
- Requires current password verification
- Security event logged on success
- Existing sessions remain valid (tokens not invalidated)

**Permissions:**
- Requires authentication
- User can only change own password
        """,
        tags=["User Management"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "current_password": {
                        "type": "string",
                        "format": "password",
                        "description": "Current password",
                    },
                    "new_password": {
                        "type": "string",
                        "format": "password",
                        "description": "New password (min 8 chars)",
                    },
                },
                "required": ["current_password", "new_password"],
            }
        },
        responses={
            200: OpenApiResponse(
                response=PasswordChangeSuccessSerializer,
                description="Password changed successfully",
                examples=[
                    OpenApiExample(
                        name="Success",
                        value={"detail": "Password changed successfully."},
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        name="Incorrect Current Password",
                        value={
                            "type": "about:blank",
                            "title": "Validation Error",
                            "status": 400,
                            "detail": "Request validation failed",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "errors": [
                                {
                                    "field": "current_password",
                                    "message": "Current password is incorrect.",
                                    "code": "invalid",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        name="Weak New Password",
                        value={
                            "type": "about:blank",
                            "title": "Validation Error",
                            "status": 400,
                            "detail": "Request validation failed",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "errors": [
                                {
                                    "field": "new_password",
                                    "message": "This password is too common.",
                                    "code": "password_too_common",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
        },
    ),
)


# ============================================================================
# Role ViewSet Schemas
# ============================================================================

role_viewset_schema = extend_schema_view(
    list=extend_schema(
        operation_id="auth_roles_list",
        summary="List roles in tenant",
        description="""
Retrieve all roles within the authenticated user's tenant/organization.

**Response:**
- Array of role objects with permission lists
- Automatically scoped to current tenant

**Permissions:**
- Requires authentication
- Returns only roles in same tenant
        """,
        tags=["Role Management"],
        responses={
            200: OpenApiResponse(description="List of roles"),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
        },
    ),
    retrieve=extend_schema(
        operation_id="auth_roles_retrieve",
        summary="Get role details",
        description="""
Retrieve detailed information about a specific role.

**Returns:**
- Role name
- Full permission list
- Creation timestamp

**Permissions:**
- Requires authentication
- Role must be in same tenant
        """,
        tags=["Role Management"],
        responses={
            200: OpenApiResponse(description="Role details"),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Role not found",
            ),
        },
    ),
    create=extend_schema(
        operation_id="auth_roles_create",
        summary="Create new role",
        description="""
Create a new role in the current tenant/organization.

**Required Fields:**
- name (string): Role name (unique within tenant)
- permissions (array): List of permission strings

**Permission Format:**
Each permission string must follow format: `module.action`

**Valid Modules:**
- users, roles, clients, suppliers, inventory, sales, purchases, finance, reports

**Valid Actions:**
- view, create, edit, delete, manage

**Examples:**
- "users.view" - View users
- "sales.create" - Create sales orders
- "reports.view" - View reports
- "inventory.manage" - Full inventory access

**Validation:**
- Name uniqueness checked within tenant
- All permissions validated against allowed modules/actions
- Creates role in same tenant as requester

**Permissions:**
- Requires authentication
        """,
        tags=["Role Management"],
        responses={
            201: OpenApiResponse(description="Role created successfully"),
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        name="Invalid Permission Format",
                        value={
                            "type": "about:blank",
                            "title": "Validation Error",
                            "status": 400,
                            "detail": "Request validation failed",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "errors": [
                                {
                                    "field": "permissions",
                                    "message": "Invalid permission format: users-view. Expected 'module.action'.",
                                    "code": "invalid",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        name="Invalid Module",
                        value={
                            "type": "about:blank",
                            "title": "Validation Error",
                            "status": 400,
                            "detail": "Request validation failed",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "errors": [
                                {
                                    "field": "permissions",
                                    "message": "Invalid module: invalid_module. Valid: users, roles, clients, suppliers, inventory, sales, purchases, finance, reports",
                                    "code": "invalid",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
        },
    ),
    partial_update=extend_schema(
        operation_id="auth_roles_partial_update",
        summary="Update role",
        description="""
Partially update role information.

**Updatable Fields:**
- name: Role name (must remain unique within tenant)
- permissions: Permission list (replaces existing permissions)

**Notes:**
- All fields optional for PATCH request
- Permission format and validation same as create
- Changes affect all users with this role

**Permissions:**
- Requires authentication
- Role must be in same tenant
        """,
        tags=["Role Management"],
        responses={
            200: OpenApiResponse(description="Role updated successfully"),
            400: OpenApiResponse(
                response=ValidationErrorSerializer,
                description="Validation error",
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Role not found",
            ),
        },
    ),
    destroy=extend_schema(
        operation_id="auth_roles_destroy",
        summary="Delete role",
        description="""
Delete a role from the system.

**Validation:**
- Role must not be assigned to any users
- Returns 400 error if users are assigned

**Recommendation:**
Before deleting a role:
1. Reassign all users to different roles
2. Verify no users have this role
3. Then delete the role

**Permissions:**
- Requires authentication
- Role must be in same tenant

**Response:**
- 204: Role deleted successfully (no content)
        """,
        tags=["Role Management"],
        responses={
            204: OpenApiResponse(description="Role deleted successfully"),
            400: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Cannot delete role assigned to users",
                examples=[
                    OpenApiExample(
                        name="Role In Use",
                        value={
                            "type": "about:blank",
                            "title": "Bad Request",
                            "status": 400,
                            "detail": "Cannot delete role assigned to users.",
                            "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Role not found",
            ),
        },
    ),
)


# ============================================================================
# Branch ViewSet Schemas
# ============================================================================

branch_viewset_schema = extend_schema_view(
    list=extend_schema(
        operation_id="auth_branches_list",
        summary="List active branches in tenant",
        description="""
Retrieve all active branches within the authenticated user's tenant/organization.

**Filters:**
- Only active branches (is_active=True)
- Automatically scoped to current tenant

**Response:**
- Array of branch objects with location details

**Use Cases:**
- Populate branch selection dropdowns
- Display available locations
- User default branch assignment

**Permissions:**
- Requires authentication
- Returns only branches in same tenant
        """,
        tags=["Branch Management"],
        responses={
            200: OpenApiResponse(description="List of active branches"),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
        },
    ),
    retrieve=extend_schema(
        operation_id="auth_branches_retrieve",
        summary="Get branch details",
        description="""
Retrieve detailed information about a specific branch.

**Returns:**
- Branch name
- Physical address
- Active status
- Creation timestamp

**Permissions:**
- Requires authentication
- Branch must be in same tenant
        """,
        tags=["Branch Management"],
        responses={
            200: OpenApiResponse(description="Branch details"),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Unauthorized",
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Branch not found",
            ),
        },
    ),
)
