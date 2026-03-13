"""
Structured sync operation logging for SC-022 compliance.

Provides comprehensive logging for all sync operations including:
- Push/pull operations with full context
- Conflict detection and resolution
- Operation processing and failures
- Retry attempts and error tracking

All sync events are logged to the 'sync' logger which should be
configured to write to a dedicated sync log file in production.

Log Levels:
- ERROR: Sync failures requiring intervention
- WARNING: Conflicts, retries, validation issues
- INFO: Successful sync operations, conflict resolution
- DEBUG: Detailed operation processing for troubleshooting

Event Types:
- SYNC_PUSH_*: Push operation lifecycle events
- SYNC_PULL_*: Pull operation lifecycle events
- SYNC_OPERATION_*: Individual operation processing
- SYNC_CONFLICT_*: Conflict detection and resolution
- SYNC_RETRY_*: Retry attempt tracking
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

logger = logging.getLogger("sync")


class SyncEventType:
    """Sync event type constants for structured logging."""

    # Push operations
    SYNC_PUSH_START = "SYNC_PUSH_START"
    SYNC_PUSH_COMPLETE = "SYNC_PUSH_COMPLETE"
    SYNC_PUSH_FAILED = "SYNC_PUSH_FAILED"

    # Pull operations
    SYNC_PULL_START = "SYNC_PULL_START"
    SYNC_PULL_COMPLETE = "SYNC_PULL_COMPLETE"
    SYNC_PULL_FAILED = "SYNC_PULL_FAILED"

    # Operation processing
    SYNC_OPERATION_APPLIED = "SYNC_OPERATION_APPLIED"
    SYNC_OPERATION_REJECTED = "SYNC_OPERATION_REJECTED"
    SYNC_OPERATION_SKIPPED = "SYNC_OPERATION_SKIPPED"
    SYNC_OPERATION_FAILED = "SYNC_OPERATION_FAILED"

    # Conflict handling
    SYNC_CONFLICT_DETECTED = "SYNC_CONFLICT_DETECTED"
    SYNC_CONFLICT_RESOLVED = "SYNC_CONFLICT_RESOLVED"
    SYNC_CONFLICT_FAILED = "SYNC_CONFLICT_FAILED"

    # Retry handling
    SYNC_RETRY_ATTEMPT = "SYNC_RETRY_ATTEMPT"
    SYNC_RETRY_EXHAUSTED = "SYNC_RETRY_EXHAUSTED"
    SYNC_RETRY_SUCCESS = "SYNC_RETRY_SUCCESS"


class SyncLogger:
    """
    Sync operation logging for SC-022 compliance.

    Provides consistent structured logging for all sync operations
    with full context for audit trail and troubleshooting.

    Usage:
        from apps.sync.logging import SyncLogger

        SyncLogger.log_sync_push_start(
            tenant_id=tenant.id,
            device_id='POS-001',
            operation_count=5,
            user_id=user.id
        )
    """

    @staticmethod
    def _serialize_value(value):
        """
        Recursively serialize values for JSON encoding.

        Converts UUIDs to strings and handles nested structures.
        """
        if isinstance(value, UUID):
            return str(value)
        elif isinstance(value, dict):
            return {k: SyncLogger._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [SyncLogger._serialize_value(item) for item in value]
        return value

    @staticmethod
    def _format_event(event_type: str, severity: str, message: str, **metadata) -> str:
        """
        Format sync event with structured metadata.

        Returns JSON-formatted string for structured logging.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "severity": severity,
            "message": message,
            **{k: SyncLogger._serialize_value(v) for k, v in metadata.items()},
        }
        return json.dumps(event)

    # Push Operation Logging

    @classmethod
    def log_sync_push_start(
        cls,
        tenant_id: UUID,
        device_id: str,
        operation_count: int,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        request_ip: Optional[str] = None,
    ) -> None:
        """
        Log start of sync push operation.

        SEVERITY: INFO - Normal sync operation initiated.

        Args:
            tenant_id: Tenant performing the sync
            device_id: Device identifier (e.g., POS-001)
            operation_count: Number of operations being pushed
            user_id: User initiating the sync
            session_id: Sync session ID
            request_ip: Client IP address
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_PUSH_START,
            severity="INFO",
            message=f"Sync push started: device={device_id}, operations={operation_count}",
            tenant_id=tenant_id,
            device_id=device_id,
            operation_count=operation_count,
            user_id=user_id,
            session_id=session_id,
            request_ip=request_ip,
        )
        logger.info(event)

    @classmethod
    def log_sync_push_complete(
        cls,
        tenant_id: UUID,
        device_id: str,
        operations_count: int,
        operations_applied: int,
        operations_skipped: int,
        operations_rejected: int,
        conflicts_detected: int,
        duration_ms: float,
        session_id: Optional[UUID] = None,
    ) -> None:
        """
        Log successful completion of sync push.

        SEVERITY: INFO - Sync completed successfully.

        Args:
            tenant_id: Tenant performing the sync
            device_id: Device identifier
            operations_count: Total operations received
            operations_applied: Successfully applied operations
            operations_skipped: Skipped (idempotent) operations
            operations_rejected: Rejected operations
            conflicts_detected: Number of conflicts detected
            duration_ms: Operation duration in milliseconds
            session_id: Sync session ID
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_PUSH_COMPLETE,
            severity="INFO",
            message=f"Sync push complete: device={device_id}, applied={operations_applied}/{operations_count}",
            tenant_id=tenant_id,
            device_id=device_id,
            operations_count=operations_count,
            operations_applied=operations_applied,
            operations_skipped=operations_skipped,
            operations_rejected=operations_rejected,
            conflicts_detected=conflicts_detected,
            duration_ms=duration_ms,
            session_id=session_id,
            success_rate=round(
                (operations_applied / operations_count * 100) if operations_count > 0 else 0, 2
            ),
        )
        logger.info(event)

    @classmethod
    def log_sync_push_failed(
        cls,
        tenant_id: UUID,
        device_id: str,
        error: str,
        operation_count: int,
        operations_processed: int,
        session_id: Optional[UUID] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Log sync push failure.

        SEVERITY: ERROR - Sync operation failed, requires intervention.

        Args:
            tenant_id: Tenant performing the sync
            device_id: Device identifier
            error: Error message
            operation_count: Total operations attempted
            operations_processed: Operations processed before failure
            session_id: Sync session ID
            error_code: Error code for categorization
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_PUSH_FAILED,
            severity="ERROR",
            message=f"Sync push failed: device={device_id}, error={error}",
            tenant_id=tenant_id,
            device_id=device_id,
            error=error,
            error_code=error_code,
            operation_count=operation_count,
            operations_processed=operations_processed,
            session_id=session_id,
        )
        logger.error(event)

    # Pull Operation Logging

    @classmethod
    def log_sync_pull_start(
        cls,
        tenant_id: UUID,
        device_id: str,
        since_timestamp: Optional[datetime],
        entity_types: Optional[list],
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        request_ip: Optional[str] = None,
    ) -> None:
        """
        Log start of sync pull operation.

        SEVERITY: INFO - Normal sync operation initiated.

        Args:
            tenant_id: Tenant performing the sync
            device_id: Device identifier
            since_timestamp: Last sync timestamp
            entity_types: Entity types being pulled
            user_id: User initiating the sync
            session_id: Sync session ID
            request_ip: Client IP address
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_PULL_START,
            severity="INFO",
            message=f"Sync pull started: device={device_id}, since={since_timestamp}",
            tenant_id=tenant_id,
            device_id=device_id,
            since_timestamp=since_timestamp.isoformat() if since_timestamp else None,
            entity_types=entity_types,
            user_id=user_id,
            session_id=session_id,
            request_ip=request_ip,
        )
        logger.info(event)

    @classmethod
    def log_sync_pull_complete(
        cls,
        tenant_id: UUID,
        device_id: str,
        changes_count: int,
        entity_breakdown: Dict[str, int],
        duration_ms: float,
        has_more: bool,
        session_id: Optional[UUID] = None,
    ) -> None:
        """
        Log successful completion of sync pull.

        SEVERITY: INFO - Sync completed successfully.

        Args:
            tenant_id: Tenant performing the sync
            device_id: Device identifier
            changes_count: Total changes returned
            entity_breakdown: Changes per entity type
            duration_ms: Operation duration in milliseconds
            has_more: Whether more changes are pending
            session_id: Sync session ID
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_PULL_COMPLETE,
            severity="INFO",
            message=f"Sync pull complete: device={device_id}, changes={changes_count}",
            tenant_id=tenant_id,
            device_id=device_id,
            changes_count=changes_count,
            entity_breakdown=entity_breakdown,
            duration_ms=duration_ms,
            has_more=has_more,
            session_id=session_id,
        )
        logger.info(event)

    @classmethod
    def log_sync_pull_failed(
        cls,
        tenant_id: UUID,
        device_id: str,
        error: str,
        session_id: Optional[UUID] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Log sync pull failure.

        SEVERITY: ERROR - Sync operation failed, requires intervention.

        Args:
            tenant_id: Tenant performing the sync
            device_id: Device identifier
            error: Error message
            session_id: Sync session ID
            error_code: Error code for categorization
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_PULL_FAILED,
            severity="ERROR",
            message=f"Sync pull failed: device={device_id}, error={error}",
            tenant_id=tenant_id,
            device_id=device_id,
            error=error,
            error_code=error_code,
            session_id=session_id,
        )
        logger.error(event)

    # Operation Processing Logging

    @classmethod
    def log_operation_applied(
        cls,
        operation_id: UUID,
        entity_type: str,
        operation_type: str,
        entity_id: str,
        tenant_id: UUID,
        device_id: str,
        processing_time_ms: Optional[float] = None,
    ) -> None:
        """
        Log successful operation application.

        SEVERITY: DEBUG - Detailed operation tracking.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity (Product, Sale, etc.)
            operation_type: CREATE, UPDATE, DELETE
            entity_id: Entity identifier
            tenant_id: Tenant ID
            device_id: Device identifier
            processing_time_ms: Time to process operation
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_OPERATION_APPLIED,
            severity="DEBUG",
            message=f"Operation applied: {operation_type} {entity_type}",
            operation_id=operation_id,
            entity_type=entity_type,
            operation_type=operation_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            device_id=device_id,
            processing_time_ms=processing_time_ms,
        )
        logger.debug(event)

    @classmethod
    def log_operation_rejected(
        cls,
        operation_id: UUID,
        entity_type: str,
        operation_type: str,
        reason: str,
        tenant_id: UUID,
        device_id: str,
        validation_errors: Optional[Dict] = None,
    ) -> None:
        """
        Log operation rejection.

        SEVERITY: WARNING - Operation rejected, may need review.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            operation_type: CREATE, UPDATE, DELETE
            reason: Rejection reason
            tenant_id: Tenant ID
            device_id: Device identifier
            validation_errors: Detailed validation errors
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_OPERATION_REJECTED,
            severity="WARNING",
            message=f"Operation rejected: {entity_type} - {reason}",
            operation_id=operation_id,
            entity_type=entity_type,
            operation_type=operation_type,
            reason=reason,
            tenant_id=tenant_id,
            device_id=device_id,
            validation_errors=validation_errors,
        )
        logger.warning(event)

    @classmethod
    def log_operation_skipped(
        cls,
        operation_id: UUID,
        entity_type: str,
        reason: str,
        tenant_id: UUID,
        device_id: str,
    ) -> None:
        """
        Log operation skipped (idempotency).

        SEVERITY: DEBUG - Operation already processed.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            reason: Skip reason (usually 'already_exists')
            tenant_id: Tenant ID
            device_id: Device identifier
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_OPERATION_SKIPPED,
            severity="DEBUG",
            message=f"Operation skipped: {entity_type} - {reason}",
            operation_id=operation_id,
            entity_type=entity_type,
            reason=reason,
            tenant_id=tenant_id,
            device_id=device_id,
        )
        logger.debug(event)

    @classmethod
    def log_operation_failed(
        cls,
        operation_id: UUID,
        entity_type: str,
        error: str,
        tenant_id: UUID,
        device_id: str,
        retry_count: int = 0,
        will_retry: bool = False,
    ) -> None:
        """
        Log operation processing failure.

        SEVERITY: ERROR - Operation failed, may retry.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            error: Error message
            tenant_id: Tenant ID
            device_id: Device identifier
            retry_count: Current retry attempt number
            will_retry: Whether operation will be retried
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_OPERATION_FAILED,
            severity="ERROR",
            message=f"Operation failed: {entity_type} - {error}",
            operation_id=operation_id,
            entity_type=entity_type,
            error=error,
            tenant_id=tenant_id,
            device_id=device_id,
            retry_count=retry_count,
            will_retry=will_retry,
        )
        logger.error(event)

    # Conflict Logging

    @classmethod
    def log_conflict_detected(
        cls,
        operation_id: UUID,
        entity_type: str,
        entity_id: str,
        resolution_rule: str,
        tenant_id: UUID,
        device_id: str,
        conflict_details: Optional[Dict] = None,
    ) -> None:
        """
        Log conflict detection.

        SEVERITY: WARNING - Conflict requires resolution.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            entity_id: Entity identifier
            resolution_rule: Resolution rule to apply
            tenant_id: Tenant ID
            device_id: Device identifier
            conflict_details: Additional conflict context
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_CONFLICT_DETECTED,
            severity="WARNING",
            message=f"Conflict detected: {entity_type} {entity_id} - {resolution_rule}",
            operation_id=operation_id,
            entity_type=entity_type,
            entity_id=entity_id,
            resolution_rule=resolution_rule,
            tenant_id=tenant_id,
            device_id=device_id,
            conflict_details=conflict_details,
        )
        logger.warning(event)

    @classmethod
    def log_conflict_resolved(
        cls,
        operation_id: UUID,
        entity_type: str,
        entity_id: str,
        resolution_rule: str,
        resolution_action: str,
        tenant_id: UUID,
        device_id: str,
        audit_log: Optional[Dict] = None,
        merged_payload: bool = False,
    ) -> None:
        """
        Log successful conflict resolution.

        SEVERITY: INFO - Conflict resolved according to rules.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            entity_id: Entity identifier
            resolution_rule: Rule applied
            resolution_action: Action taken (APPLY, MERGE, REJECT, etc.)
            tenant_id: Tenant ID
            device_id: Device identifier
            audit_log: Full resolution audit trail
            merged_payload: Whether payload was merged
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_CONFLICT_RESOLVED,
            severity="INFO",
            message=f"Conflict resolved: {entity_type} - {resolution_action}",
            operation_id=operation_id,
            entity_type=entity_type,
            entity_id=entity_id,
            resolution_rule=resolution_rule,
            resolution_action=resolution_action,
            tenant_id=tenant_id,
            device_id=device_id,
            audit_log=audit_log,
            merged_payload=merged_payload,
        )
        logger.info(event)

    @classmethod
    def log_conflict_failed(
        cls,
        operation_id: UUID,
        entity_type: str,
        error: str,
        tenant_id: UUID,
        device_id: str,
        resolution_rule: Optional[str] = None,
    ) -> None:
        """
        Log conflict resolution failure.

        SEVERITY: ERROR - Conflict resolution failed.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            error: Error message
            tenant_id: Tenant ID
            device_id: Device identifier
            resolution_rule: Rule attempted
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_CONFLICT_FAILED,
            severity="ERROR",
            message=f"Conflict resolution failed: {entity_type} - {error}",
            operation_id=operation_id,
            entity_type=entity_type,
            error=error,
            tenant_id=tenant_id,
            device_id=device_id,
            resolution_rule=resolution_rule,
        )
        logger.error(event)

    # Retry Logging

    @classmethod
    def log_retry_attempt(
        cls,
        operation_id: UUID,
        entity_type: str,
        retry_count: int,
        max_retries: int,
        tenant_id: UUID,
        device_id: str,
        previous_error: str,
    ) -> None:
        """
        Log retry attempt.

        SEVERITY: WARNING - Operation being retried.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            retry_count: Current retry attempt (1-indexed)
            max_retries: Maximum retry attempts allowed
            tenant_id: Tenant ID
            device_id: Device identifier
            previous_error: Error from previous attempt
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_RETRY_ATTEMPT,
            severity="WARNING",
            message=f"Retry attempt {retry_count}/{max_retries}: {entity_type}",
            operation_id=operation_id,
            entity_type=entity_type,
            retry_count=retry_count,
            max_retries=max_retries,
            tenant_id=tenant_id,
            device_id=device_id,
            previous_error=previous_error,
        )
        logger.warning(event)

    @classmethod
    def log_retry_exhausted(
        cls,
        operation_id: UUID,
        entity_type: str,
        retry_count: int,
        tenant_id: UUID,
        device_id: str,
        final_error: str,
    ) -> None:
        """
        Log retry attempts exhausted.

        SEVERITY: ERROR - Operation failed after all retries.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            retry_count: Total retry attempts made
            tenant_id: Tenant ID
            device_id: Device identifier
            final_error: Final error message
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_RETRY_EXHAUSTED,
            severity="ERROR",
            message=f"Retry exhausted after {retry_count} attempts: {entity_type}",
            operation_id=operation_id,
            entity_type=entity_type,
            retry_count=retry_count,
            tenant_id=tenant_id,
            device_id=device_id,
            final_error=final_error,
        )
        logger.error(event)

    @classmethod
    def log_retry_success(
        cls,
        operation_id: UUID,
        entity_type: str,
        retry_count: int,
        tenant_id: UUID,
        device_id: str,
    ) -> None:
        """
        Log successful retry.

        SEVERITY: INFO - Operation succeeded after retry.

        Args:
            operation_id: Operation UUID
            entity_type: Type of entity
            retry_count: Number of retries before success
            tenant_id: Tenant ID
            device_id: Device identifier
        """
        event = cls._format_event(
            event_type=SyncEventType.SYNC_RETRY_SUCCESS,
            severity="INFO",
            message=f"Retry successful after {retry_count} attempts: {entity_type}",
            operation_id=operation_id,
            entity_type=entity_type,
            retry_count=retry_count,
            tenant_id=tenant_id,
            device_id=device_id,
        )
        logger.info(event)
