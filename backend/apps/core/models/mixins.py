"""
Abstract model mixins for Gravitea ERP.

Provides TenantBoundModel for multi-tenant data isolation with
automatic IDOR prevention per FR-003.
"""

import logging

from django.db import models

from apps.core.managers.tenant_bound import (AllObjectsManager,
                                             TenantBoundManager,
                                             get_current_tenant_id)

logger = logging.getLogger("security")


def _get_security_logger():
    """Return the SecurityLogger class via the shared helper (M-001)."""
    try:
        from apps.core.security import get_security_logger
        return get_security_logger()
    except ImportError:
        return None


class TenantBoundModel(models.Model):
    """
    Abstract base class for all tenant-scoped models.

    Provides:
    - tenant_id field with automatic filtering via TenantBoundManager
    - IDOR prevention via _validate_tenant_references()
    - Unscoped access via all_objects manager

    Usage:
        class Product(TenantBoundModel):
            name = models.CharField(max_length=255)
            category = models.ForeignKey(Category, ...)

            class Meta:
                db_table = 'product'

    Security Notes:
        - All FK references are validated for same-tenant ownership on save()
        - Uses TenantBoundManager for automatic tenant filtering
        - all_objects provides unscoped access for admin/system operations

    SECURITY NOTE - BULK OPERATIONS (H-005):
        bulk_create() and bulk_update() now call _validate_tenant_references()
        on every object before delegating to the database.  QuerySet.update()
        still bypasses per-object validation (direct SQL) -- only use it
        with system-controlled data or manually verified tenant ownership.
    """

    tenant_id = models.UUIDField(db_index=True, help_text="Parent tenant UUID for data isolation")

    # Default manager with tenant filtering
    objects = TenantBoundManager()

    # Unscoped manager for system operations
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Save with IDOR prevention validation.

        Validates that all FK references belong to the same tenant
        before saving to prevent cross-tenant data access.
        """
        # Set tenant_id from context if not already set
        if not self.tenant_id:
            current_tenant = get_current_tenant_id()
            if current_tenant:
                self.tenant_id = current_tenant
            else:
                raise ValueError(
                    "Cannot save TenantBoundModel without tenant_id. "
                    "Set tenant_id explicitly or ensure tenant context is active."
                )

        # Validate FK references belong to same tenant
        self._validate_tenant_references()

        super().save(*args, **kwargs)

    def _validate_tenant_references(self):
        """
        Ensure all FK references belong to the same tenant.

        This prevents IDOR attacks where an attacker tries to
        reference entities from another tenant.

        Raises:
            ValueError: If any FK reference belongs to a different tenant.
        """
        for field in self._meta.get_fields():
            if not isinstance(field, models.ForeignKey):
                continue

            # Skip the tenant field itself
            if field.name == "tenant":
                continue

            # Get the related object (if set)
            related_obj = getattr(self, field.name, None)
            if related_obj is None:
                continue

            # Check if related model has tenant_id
            if hasattr(related_obj, "tenant_id"):
                if related_obj.tenant_id != self.tenant_id:
                    # Log IDOR attempt with structured security logger
                    sec_logger = _get_security_logger()
                    if sec_logger:
                        sec_logger.idor_attempt(
                            model_name=self.__class__.__name__,
                            field_name=field.name,
                            current_tenant=self.tenant_id,
                            referenced_tenant=related_obj.tenant_id,
                        )
                    else:
                        logger.warning(
                            f"IDOR violation attempt: {self.__class__.__name__}.{field.name} "
                            f"references {related_obj.__class__.__name__} from different tenant. "
                            f"Current tenant: {self.tenant_id}, "
                            f"Referenced tenant: {related_obj.tenant_id}"
                        )
                    raise ValueError(
                        f"IDOR violation: {field.name} belongs to a different tenant. "
                        f"Cross-tenant references are not allowed."
                    )


class TimestampedModel(models.Model):
    """
    Abstract model with creation and update timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract model with soft delete capability.
    """

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark record as inactive instead of deleting."""
        self.is_active = False
        self.save(update_fields=["is_active"])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_active = True
        self.save(update_fields=["is_active"])
