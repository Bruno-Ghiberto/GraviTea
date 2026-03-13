"""
Authentication models for Gravitea ERP.

Provides Role and AppUser models with tenant-bound isolation
and RBAC permission management.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.managers.tenant_bound import (AllObjectsManager)
from apps.core.models.branch import Branch
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class Role(TenantBoundModel):
    """
    Permission groups for RBAC within a tenant.

    Defines a set of permissions that can be assigned to users.
    Each tenant can have multiple custom roles.

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        name: Role name (unique per tenant)
        permissions: List of permission strings
        created_at: Record creation timestamp

    Permissions Schema:
        [
            "inventory.read",
            "inventory.write",
            "sales.create",
            "reports.view"
        ]

    Permission Format: {module}.{action}
        Modules: inventory, sales, purchases, customers, reports, settings
        Actions: read, write, create, delete, admin
    """

    VALID_MODULES = {"inventory", "sales", "purchases", "customers", "reports", "settings"}
    VALID_ACTIONS = {"read", "write", "create", "delete", "admin", "export"}

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=100, help_text="Role name (e.g., 'Vendedor', 'Gerente')")
    permissions = models.JSONField(default=list, help_text="List of permission strings")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role"
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "name"], name="unique_role_per_tenant"),
        ]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    def clean(self):
        """Validate permission strings."""
        errors = []

        if not isinstance(self.permissions, list):
            raise ValidationError({"permissions": "Permissions must be a list."})

        for perm in self.permissions:
            if not isinstance(perm, str):
                errors.append(f"Permission must be a string: {perm}")
                continue

            parts = perm.split(".")
            if len(parts) != 2:
                errors.append(f"Invalid permission format: {perm}. Expected 'module.action'.")
                continue

            module, action = parts
            if module not in self.VALID_MODULES:
                errors.append(f"Invalid module in permission: {perm}. Valid: {self.VALID_MODULES}")
            if action not in self.VALID_ACTIONS:
                errors.append(f"Invalid action in permission: {perm}. Valid: {self.VALID_ACTIONS}")

        if errors:
            raise ValidationError({"permissions": errors})

    def save(self, *args, **kwargs):
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        self.full_clean()
        super().save(*args, **kwargs)

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions

    def has_module_permission(self, module: str, action: str = None) -> bool:
        """
        Check if role has permission for a module.

        Args:
            module: Module name (e.g., 'inventory')
            action: Optional specific action (e.g., 'write')

        Returns:
            True if role has the permission.
        """
        if action:
            return f"{module}.{action}" in self.permissions

        # Check if any permission for the module exists
        return any(p.startswith(f"{module}.") for p in self.permissions)


class AppUserManager(BaseUserManager):
    """
    Custom user manager for AppUser model.

    Handles tenant-aware user creation.
    """

    def create_user(self, email, tenant, password=None, **extra_fields):
        """
        Create and return a regular user.

        Args:
            email: User's email address.
            tenant: Tenant instance the user belongs to.
            password: Optional password.
            **extra_fields: Additional user fields.

        Returns:
            Created AppUser instance.
        """
        if not email:
            raise ValueError("Email is required")
        if not tenant:
            raise ValueError("Tenant is required")

        email = self.normalize_email(email)
        user = self.model(email=email, tenant=tenant, tenant_id=tenant.id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create a superuser.

        Note: Superusers still require a tenant context.
        For admin operations, create a dedicated admin tenant.
        """
        extra_fields.setdefault("is_active", True)

        # For superuser, we need a tenant - create or use default
        # Use FREE plan to avoid valid_until requirement
        from apps.core.models import Tenant

        admin_tenant, _ = Tenant.objects.get_or_create(
            name="System Admin", defaults={"plan_type": "FREE"}
        )

        return self.create_user(email, admin_tenant, password, **extra_fields)


class AppUser(AbstractBaseUser, TenantBoundModel):
    """
    Application user (employee) within a tenant.

    Custom user model with tenant isolation and role-based access control.

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        email: Login email (unique per tenant)
        full_name: Display name
        role: Assigned role (FK, same tenant)
        default_branch: Default working branch (FK, same tenant)
        last_login: Last successful login timestamp
        is_active: Account active flag
        created_at: Record creation timestamp
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users",
    )
    email = models.EmailField(max_length=255, help_text="Login email address")
    full_name = models.CharField(
        max_length=255, null=True, blank=True, help_text="User's display name"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Assigned role for permissions",
    )
    default_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_users",
        help_text="Default working branch",
    )
    is_active = models.BooleanField(default=True, db_index=True, help_text="Active account flag")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppUserManager()
    all_objects = AllObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "app_user"
        ordering = ["email"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "email"],
                name="unique_email_per_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.email} ({self.tenant.name})"

    def save(self, *args, **kwargs):
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        super().save(*args, **kwargs)

    @property
    def default_branch_id(self):
        """Get default_branch ID for JWT claims."""
        return self.default_branch.id if self.default_branch else None

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission via their role.

        Args:
            permission: Permission string (e.g., 'inventory.write')

        Returns:
            True if user's role has the permission.
        """
        if not self.role:
            return False
        return self.role.has_permission(permission)

    def has_module_permission(self, module: str, action: str = None) -> bool:
        """Check if user has permission for a module."""
        if not self.role:
            return False
        return self.role.has_module_permission(module, action)

    def get_permissions(self) -> list:
        """Get list of all permissions for this user."""
        if not self.role:
            return []
        return list(self.role.permissions)
