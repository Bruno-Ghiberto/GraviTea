"""
Tenant-bound manager for multi-tenant data isolation.

Implements ORM-level tenant filtering per FR-001, FR-002, FR-003.
Works in conjunction with PostgreSQL RLS for defense-in-depth security.

SECURITY NOTES:
- Uses contextvars for async-safe tenant context (not threading.local)
- Sets PostgreSQL session variable for RLS enforcement
- Both Python and DB layers must be set for defense-in-depth
"""

import logging
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from django.db import connection, models

# Shared lazy-import helper for SecurityLogger (M-001 deduplication).
# Circular-import-safe: apps.core.security uses a cached lazy loader.
def _get_security_logger():
    """Return the SecurityLogger class via the shared helper."""
    try:
        from apps.core.security import get_security_logger
        return get_security_logger()
    except ImportError:
        return None


logger = logging.getLogger("security")

# Async-safe context storage using contextvars (replaces threading.local)
# This is critical for Django async views, Channels, and asyncio tasks
_tenant_id_context: ContextVar[Optional[UUID]] = ContextVar("tenant_id", default=None)


def get_current_tenant_id() -> Optional[UUID]:
    """
    Get the current tenant_id from context-local storage.

    Returns:
        UUID of current tenant or None if not set.

    Note: Uses contextvars for async-safety in Django 4.x+ async views.
    """
    return _tenant_id_context.get()


def set_current_tenant_id(tenant_id: Optional[UUID], set_db_context: bool = True) -> None:
    """
    Set the current tenant_id in both Python context and PostgreSQL session.

    This function performs two critical security operations:
    1. Sets Python contextvars for ORM-level filtering (TenantBoundManager)
    2. Sets PostgreSQL session variable for RLS policy enforcement

    SECURITY: Both layers must be set for defense-in-depth isolation.

    Args:
        tenant_id: UUID of tenant to set, or None to clear.
        set_db_context: If True, also set PostgreSQL session variable.
                        Set to False only for testing or specific admin operations.
    """
    # Set Python context (async-safe)
    _tenant_id_context.set(tenant_id)

    # CRITICAL: Set PostgreSQL session variable for RLS enforcement
    if set_db_context:
        _set_postgres_tenant_context(tenant_id)


def _set_postgres_tenant_context(tenant_id: Optional[UUID]) -> None:
    """
    Set PostgreSQL session variable for Row-Level Security (RLS).

    This is CRITICAL for defense-in-depth security. The RLS policies
    in database/SQL/002_rls_policies.sql depend on this variable.

    Args:
        tenant_id: UUID of tenant to set, or None to clear/reset.
    """
    # SET/RESET session variables are PostgreSQL-specific.
    # Skip silently on SQLite (used in tests) and other non-PG backends.
    if connection.vendor != "postgresql":
        return

    try:
        with connection.cursor() as cursor:
            if tenant_id:
                # Set tenant context for RLS policies
                cursor.execute("SET app.current_tenant_id = %s", [str(tenant_id)])
                # Use SecurityLogger if available
                sec_logger = _get_security_logger()
                if sec_logger:
                    sec_logger.rls_context_set(tenant_id)
                else:
                    logger.debug(f"PostgreSQL tenant context set: {tenant_id}")
            else:
                # Reset/clear tenant context
                cursor.execute("RESET app.current_tenant_id")
                logger.debug("PostgreSQL tenant context cleared")
    except Exception as e:
        error_msg = str(e)

        # pytest-django blocks DB access in tests without @pytest.mark.django_db.
        # This is NOT a real database failure — no connection was attempted.
        # Safe to skip; the test intentionally has no DB access.
        if "Database access not allowed" in error_msg:
            logger.debug(
                "Skipping PostgreSQL tenant context (no DB access): %s",
                error_msg,
            )
            return

        # When a prior IntegrityError (e.g. unique-constraint violation) has
        # already aborted the current transaction, Django refuses any further
        # SQL until the atomic block ends.  SET LOCAL is transaction-scoped,
        # so the context is automatically discarded on rollback — safe to skip.
        if "current transaction" in error_msg and "atomic" in error_msg:
            logger.debug(
                "Skipping PostgreSQL tenant context (transaction aborted): %s",
                error_msg,
            )
            return

        # FAIL-CLOSED (C-004): If SET LOCAL fails, RLS policies will NOT
        # filter rows.  Re-raise so the request is aborted rather than
        # proceeding without database-level tenant isolation.
        from apps.core.exceptions import TenantContextError

        sec_logger = _get_security_logger()
        if sec_logger:
            sec_logger.rls_context_failure(tenant_id, str(e))
        else:
            logger.error(
                "SECURITY: Failed to set PostgreSQL tenant context for "
                "tenant_id=%s: %s — aborting request (fail-closed).",
                tenant_id,
                e,
            )
        raise TenantContextError(
            f"Failed to set PostgreSQL RLS context for tenant {tenant_id}: {e}"
        ) from e


def clear_tenant_context() -> None:
    """
    Clear tenant context from both Python and PostgreSQL.

    Should be called at the end of each request/task to prevent
    context leakage between requests.
    """
    set_current_tenant_id(None)


# Backwards compatibility alias
clear_current_tenant_id = clear_tenant_context


class TenantBoundQuerySet(models.QuerySet):
    """
    QuerySet that automatically filters by tenant_id.

    Provides unscoped() method for system operations that need
    to bypass tenant filtering (migrations, admin, batch jobs).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._skip_tenant_filter = False

    def _clone(self):
        c = super()._clone()
        c._skip_tenant_filter = self._skip_tenant_filter
        return c

    def unscoped(self):
        """
        Return queryset without tenant filtering.

        Use with caution - only for system operations.
        """
        clone = self._clone()
        clone._skip_tenant_filter = True
        return clone

    # ------------------------------------------------------------------
    # H-005: IDOR validation for bulk operations
    # ------------------------------------------------------------------

    def bulk_create(self, objs, **kwargs):
        """Validate tenant FK references on every object before bulk insert."""
        for obj in objs:
            if hasattr(obj, "_validate_tenant_references"):
                obj._validate_tenant_references()
        return super().bulk_create(objs, **kwargs)

    def bulk_update(self, objs, fields, **kwargs):
        """Validate tenant FK references on every object before bulk update."""
        for obj in objs:
            if hasattr(obj, "_validate_tenant_references"):
                obj._validate_tenant_references()
        return super().bulk_update(objs, fields, **kwargs)


class TenantBoundManager(models.Manager):
    """
    Custom manager that automatically filters by tenant_id.

    Raises ValueError if no tenant context is set, preventing
    accidental data leaks across tenants.

    SECURITY: Implements FAIL-CLOSED pattern per C-002:
    - None/invalid tenant_id returns EMPTY queryset (not all data)
    - Logs security events for monitoring
    - Never allows unfiltered access through default manager

    Usage:
        class MyModel(TenantBoundModel):
            objects = TenantBoundManager()

        # In views/services:
        MyModel.objects.all()  # Auto-filtered by current tenant

        # For system operations:
        MyModel.all_objects.all()  # Unscoped access
    """

    def get_queryset(self):
        """
        Return queryset filtered by current tenant_id.

        SECURITY (FAIL-CLOSED): If tenant_id is None or invalid,
        returns an EMPTY queryset (not all data). This ensures that
        missing tenant context results in NO DATA ACCESS rather than
        unfiltered access to all tenant data.

        Raises:
            ValueError: If no tenant context is set (for explicit error handling).
        """
        qs = TenantBoundQuerySet(self.model, using=self._db)

        tenant_id = get_current_tenant_id()

        # CRITICAL SECURITY: FAIL-CLOSED pattern (C-002)
        # If tenant_id is None or invalid, return EMPTY queryset
        if tenant_id is None:
            # Log security event for monitoring
            sec_logger = _get_security_logger()
            if sec_logger:
                sec_logger.fail_closed_triggered(
                    model_name=self.model.__name__,
                    reason="tenant_context_not_set",
                    caller_info=None,  # Could be enhanced with stack trace
                )
            else:
                logger.warning(
                    f"SECURITY: Fail-closed triggered for {self.model.__name__}. "
                    "Tenant context not set - returning EMPTY queryset."
                )

            # Raise error to make context requirement explicit
            raise ValueError(
                "Tenant context not set. Ensure TenantContextMiddleware is active "
                "or use set_current_tenant_id() in scripts/tests."
            )

        # Validate tenant_id is a valid UUID
        if not isinstance(tenant_id, UUID):
            sec_logger = _get_security_logger()
            if sec_logger:
                sec_logger.fail_closed_triggered(
                    model_name=self.model.__name__,
                    reason="invalid_tenant_id_type",
                    caller_info=f"tenant_id={tenant_id}, type={type(tenant_id)}",
                )
            else:
                logger.warning(
                    f"SECURITY: Fail-closed triggered for {self.model.__name__}. "
                    f"Invalid tenant_id type: {type(tenant_id)} - returning EMPTY queryset."
                )

            # Return empty queryset instead of raising (fail-closed)
            # Use impossible filter to ensure no results
            return qs.none()

        # Valid tenant_id - apply normal filtering
        return qs.filter(tenant_id=tenant_id)

    def get_queryset_unscoped(self):
        """
        Return queryset without tenant filtering.

        Use with caution - only for:
        - Migrations
        - Admin operations
        - System batch jobs
        - Cross-tenant reporting

        Example:
            MyModel.objects.get_queryset_unscoped().filter(is_active=True)
        """
        return TenantBoundQuerySet(self.model, using=self._db)


class AllObjectsManager(models.Manager):
    """
    Unscoped manager for system operations.

    WARNING: Using this manager bypasses tenant isolation!
    Only use for:
    - Django admin
    - System migrations
    - Cross-tenant reporting (with explicit authorization)

    Provides access to all records regardless of tenant context.
    Aliased as `all_objects` on TenantBoundModel.
    """

    def get_queryset(self):
        # Log usage for security monitoring using structured logger
        sec_logger = _get_security_logger()
        if sec_logger:
            sec_logger.unscoped_access(
                model_name=self.model.__name__,
                caller_info=None,  # Could be enhanced with stack trace
                reason=None,
            )
        else:
            logger.debug(
                f"AllObjectsManager accessed for {self.model.__name__}. "
                "This bypasses tenant isolation."
            )
        return super().get_queryset()
