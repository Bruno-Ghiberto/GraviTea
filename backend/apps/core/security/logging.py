"""
Structured security logging for Gravitea ERP.

Provides specialized logging functions for security-critical events
including IDOR attempts, tenant context changes, and audit trails.

All security events are logged to the 'security' logger which should
be configured to write to a dedicated security log file in production.

Log Levels:
- CRITICAL: Active attack detected, immediate action required
- WARNING: Potential security issue, investigation needed
- INFO: Security-relevant event for audit trail
- DEBUG: Detailed security context for debugging

Event Types:
- IDOR_ATTEMPT: Cross-tenant reference attempt (FR-003)
- TENANT_CONTEXT: Tenant context set/clear events (FR-001)
- UNSCOPED_ACCESS: AllObjectsManager usage (audit trail)
- BULK_OPERATION: Bulk ops bypassing validation (warning)
- AUTH_EVENT: Authentication success/failure (audit)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger("security")


class SecurityEventType:
    """Security event type constants for structured logging."""

    IDOR_ATTEMPT = "IDOR_ATTEMPT"
    TENANT_CONTEXT_SET = "TENANT_CONTEXT_SET"
    TENANT_CONTEXT_CLEAR = "TENANT_CONTEXT_CLEAR"
    UNSCOPED_ACCESS = "UNSCOPED_ACCESS"
    BULK_OPERATION = "BULK_OPERATION"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    RLS_CONTEXT_SET = "RLS_CONTEXT_SET"
    RLS_CONTEXT_CLEAR = "RLS_CONTEXT_CLEAR"
    RLS_CONTEXT_FAILURE = "RLS_CONTEXT_FAILURE"
    FAIL_CLOSED_TRIGGERED = "FAIL_CLOSED_TRIGGERED"


class SecurityLogger:
    """
    Structured security event logger.

    Provides consistent formatting for security events with
    JSON-structured metadata for log aggregation systems.

    Usage:
        from apps.core.security import SecurityLogger

        SecurityLogger.idor_attempt(
            model_name='Product',
            field_name='supplier',
            current_tenant=uuid1,
            referenced_tenant=uuid2,
            user_id=user.id,
        )
    """

    @staticmethod
    def _format_event(event_type: str, severity: str, message: str, **metadata) -> str:
        """
        Format security event with structured metadata.

        Returns JSON-formatted string for structured logging.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "message": message,
            **{k: str(v) if isinstance(v, UUID) else v for k, v in metadata.items()},
        }
        return json.dumps(event)

    @classmethod
    def idor_attempt(
        cls,
        model_name: str,
        field_name: str,
        current_tenant: UUID,
        referenced_tenant: UUID,
        user_id: Optional[UUID] = None,
        request_path: Optional[str] = None,
        request_ip: Optional[str] = None,
    ) -> None:
        """
        Log an IDOR (Insecure Direct Object Reference) attempt.

        SEVERITY: CRITICAL - This indicates a potential attack or bug.

        Args:
            model_name: Name of the model where violation occurred
            field_name: Name of the FK field with cross-tenant reference
            current_tenant: The tenant_id of the current context
            referenced_tenant: The tenant_id of the referenced object
            user_id: ID of the user making the request (if available)
            request_path: HTTP request path (if available)
            request_ip: Client IP address (if available)
        """
        event = cls._format_event(
            event_type=SecurityEventType.IDOR_ATTEMPT,
            severity="CRITICAL",
            message=f"IDOR violation: {model_name}.{field_name} cross-tenant reference blocked",
            model=model_name,
            field=field_name,
            current_tenant=current_tenant,
            referenced_tenant=referenced_tenant,
            user_id=user_id,
            request_path=request_path,
            request_ip=request_ip,
        )
        logger.critical(event)

    @classmethod
    def tenant_context_set(
        cls,
        tenant_id: UUID,
        source: str = "middleware",
        user_id: Optional[UUID] = None,
        request_path: Optional[str] = None,
    ) -> None:
        """
        Log tenant context being set.

        SEVERITY: DEBUG - Normal operation, useful for debugging.

        Args:
            tenant_id: The tenant_id being set
            source: Where the context was set (middleware, test, script)
            user_id: ID of the authenticated user
            request_path: HTTP request path
        """
        event = cls._format_event(
            event_type=SecurityEventType.TENANT_CONTEXT_SET,
            severity="DEBUG",
            message=f"Tenant context set: {tenant_id}",
            tenant_id=tenant_id,
            source=source,
            user_id=user_id,
            request_path=request_path,
        )
        logger.debug(event)

    @classmethod
    def tenant_context_clear(cls, source: str = "middleware") -> None:
        """
        Log tenant context being cleared.

        SEVERITY: DEBUG - Normal operation.

        Args:
            source: Where the context was cleared
        """
        event = cls._format_event(
            event_type=SecurityEventType.TENANT_CONTEXT_CLEAR,
            severity="DEBUG",
            message="Tenant context cleared",
            source=source,
        )
        logger.debug(event)

    @classmethod
    def rls_context_set(cls, tenant_id: UUID) -> None:
        """Log PostgreSQL RLS context being set."""
        event = cls._format_event(
            event_type=SecurityEventType.RLS_CONTEXT_SET,
            severity="DEBUG",
            message=f"PostgreSQL RLS context set: {tenant_id}",
            tenant_id=tenant_id,
        )
        logger.debug(event)

    @classmethod
    def rls_context_failure(cls, tenant_id: Optional[UUID], error: str) -> None:
        """
        Log PostgreSQL RLS context setting failure.

        SEVERITY: ERROR - Fail-closed; request will be aborted (C-004).
        """
        event = cls._format_event(
            event_type=SecurityEventType.RLS_CONTEXT_FAILURE,
            severity="ERROR",
            message=f"Failed to set PostgreSQL RLS context: {error}",
            tenant_id=tenant_id,
            error=error,
        )
        logger.error(event)

    @classmethod
    def unscoped_access(
        cls,
        model_name: str,
        caller_info: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """
        Log usage of AllObjectsManager (unscoped access).

        SEVERITY: INFO - Legitimate but should be audited.

        Args:
            model_name: Name of the model being accessed
            caller_info: Information about the calling code
            reason: Reason for unscoped access (if provided)
        """
        event = cls._format_event(
            event_type=SecurityEventType.UNSCOPED_ACCESS,
            severity="INFO",
            message=f"Unscoped access to {model_name} (bypasses tenant isolation)",
            model=model_name,
            caller=caller_info,
            reason=reason,
        )
        logger.info(event)

    @classmethod
    def bulk_operation(
        cls,
        model_name: str,
        operation: str,
        count: int,
        tenant_id: Optional[UUID] = None,
    ) -> None:
        """
        Log bulk operation that bypasses per-record validation.

        SEVERITY: WARNING - Bulk ops skip _validate_tenant_references().

        Args:
            model_name: Name of the model
            operation: Type of operation (bulk_create, bulk_update, update)
            count: Number of records affected
            tenant_id: Current tenant context (if set)
        """
        event = cls._format_event(
            event_type=SecurityEventType.BULK_OPERATION,
            severity="WARNING",
            message=f"Bulk {operation} on {model_name}: {count} records (validation bypassed)",
            model=model_name,
            operation=operation,
            record_count=count,
            tenant_id=tenant_id,
        )
        logger.warning(event)

    @classmethod
    def auth_success(
        cls,
        user_id: UUID,
        tenant_id: UUID,
        email: str,
        request_ip: Optional[str] = None,
    ) -> None:
        """
        Log successful authentication.

        SEVERITY: INFO - Audit trail for authentication.
        """
        event = cls._format_event(
            event_type=SecurityEventType.AUTH_SUCCESS,
            severity="INFO",
            message=f"Authentication successful: {email}",
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            request_ip=request_ip,
        )
        logger.info(event)

    @classmethod
    def auth_failure(
        cls,
        email: str,
        reason: str,
        request_ip: Optional[str] = None,
    ) -> None:
        """
        Log failed authentication attempt.

        SEVERITY: WARNING - May indicate attack or credential issue.
        """
        event = cls._format_event(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity="WARNING",
            message=f"Authentication failed: {email} - {reason}",
            email=email,
            reason=reason,
            request_ip=request_ip,
        )
        logger.warning(event)

    @classmethod
    def fail_closed_triggered(
        cls,
        model_name: str,
        reason: str,
        caller_info: Optional[str] = None,
    ) -> None:
        """
        Log fail-closed security pattern triggered (C-002).

        SEVERITY: WARNING - Invalid tenant context blocked access.

        Args:
            model_name: Name of the model where fail-closed was triggered
            reason: Reason for fail-closed (tenant_context_not_set, invalid_tenant_id_type)
            caller_info: Additional caller information
        """
        event = cls._format_event(
            event_type=SecurityEventType.FAIL_CLOSED_TRIGGERED,
            severity="WARNING",
            message=f"Fail-closed security triggered for {model_name}: {reason}",
            model=model_name,
            reason=reason,
            caller=caller_info,
        )
        logger.warning(event)


# ============================================================
# Convenience Functions (for backwards compatibility)
# ============================================================


def log_idor_attempt(
    model_name: str, field_name: str, current_tenant: UUID, referenced_tenant: UUID, **kwargs
) -> None:
    """Log an IDOR violation attempt."""
    SecurityLogger.idor_attempt(
        model_name=model_name,
        field_name=field_name,
        current_tenant=current_tenant,
        referenced_tenant=referenced_tenant,
        **kwargs,
    )


def log_tenant_context_change(tenant_id: Optional[UUID], action: str = "set", **kwargs) -> None:
    """Log tenant context change (set or clear)."""
    if action == "set" and tenant_id:
        SecurityLogger.tenant_context_set(tenant_id, **kwargs)
    else:
        SecurityLogger.tenant_context_clear(**kwargs)


def log_unscoped_access(model_name: str, **kwargs) -> None:
    """Log unscoped (AllObjectsManager) access."""
    SecurityLogger.unscoped_access(model_name, **kwargs)


def log_bulk_operation_warning(model_name: str, operation: str, count: int, **kwargs) -> None:
    """Log bulk operation that bypasses validation."""
    SecurityLogger.bulk_operation(model_name, operation, count, **kwargs)


def log_authentication_event(
    success: bool,
    email: str,
    user_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None,
    reason: Optional[str] = None,
    **kwargs,
) -> None:
    """Log authentication success or failure."""
    if success:
        SecurityLogger.auth_success(user_id=user_id, tenant_id=tenant_id, email=email, **kwargs)
    else:
        SecurityLogger.auth_failure(email=email, reason=reason or "Unknown", **kwargs)
