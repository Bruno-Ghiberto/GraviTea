"""
Celery background tasks for sync operations.

Tasks:
- sync_pending_operations: Process pending sync operations for a tenant
- process_fiscal_queue: Process fiscal document queue with retry logic
- cleanup_old_sync_sessions: Cleanup old sync session records

H-003: Implements exponential backoff retry logic for transient failures
"""

import logging
from datetime import timedelta
from typing import Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("sync")


# H-003: Retry configuration constants
MAX_RETRY_ATTEMPTS = 5
RETRY_BACKOFF_BASE = 60  # Base delay in seconds
RETRY_BACKOFF_MAX = 600  # Maximum delay in seconds (10 minutes)

# Transient errors that should trigger retry
TRANSIENT_ERROR_KEYWORDS = [
    "connection",
    "timeout",
    "network",
    "unavailable",
    "temporary",
    "deadlock",
    "lock",
]


def _is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is transient and should trigger retry.

    H-003: Differentiates between transient and permanent failures.

    Args:
        error: Exception to analyze

    Returns:
        bool: True if error is transient and should be retried
    """
    error_msg = str(error).lower()
    return any(keyword in error_msg for keyword in TRANSIENT_ERROR_KEYWORDS)


@shared_task(
    bind=True,
    max_retries=MAX_RETRY_ATTEMPTS,
    default_retry_delay=RETRY_BACKOFF_BASE,
    retry_backoff=True,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    rate_limit="50/m",
)
def sync_pending_operations(self, tenant_id: str, batch_size: int = 100) -> dict:
    """
    Process pending sync operations for a tenant.

    H-003: Implements exponential backoff retry logic:
    - Retries transient failures (network, timeout, deadlock)
    - Exponential backoff: 60s, 120s, 240s, 480s, 600s
    - Logs retry attempts for monitoring
    - Permanent failures don't retry

    Args:
        tenant_id: UUID of the tenant to process operations for
        batch_size: Maximum number of operations to process in one run

    Returns:
        dict: Summary of processed operations

    Raises:
        MaxRetriesExceededError: If max retries exceeded
    """
    from apps.sync.models import PendingOperation
    from apps.sync.logging import SyncLogger

    logger.info(
        f"Processing pending operations for tenant {tenant_id} "
        f"(attempt {self.request.retries + 1}/{MAX_RETRY_ATTEMPTS + 1})"
    )

    processed = 0
    failed = 0
    skipped = 0
    transient_failures = 0

    try:
        # Get pending operations ordered by timestamp
        pending_ops = (
            PendingOperation.objects.filter(tenant_id=tenant_id, status="PENDING")
            .order_by("client_timestamp")[:batch_size]
        )

        for op in pending_ops:
            try:
                with transaction.atomic():
                    # Process the operation (actual logic would be in conflict_resolver)
                    op.status = "APPLIED"
                    op.processed_at = timezone.now()
                    op.save(update_fields=["status", "processed_at"])
                    processed += 1

            except Exception as e:
                error_msg = str(e)
                is_transient = _is_transient_error(e)

                logger.error(
                    f"Failed to process operation {op.id}: {error_msg} "
                    f"(transient={is_transient})"
                )

                # H-003: Track retry count for operations
                op.retry_count += 1

                if is_transient and op.retry_count < MAX_RETRY_ATTEMPTS:
                    # Mark as pending for retry
                    op.status = "PENDING"
                    transient_failures += 1

                    # Log retry attempt
                    SyncLogger.log_operation_failed(
                        operation_id=op.id,
                        entity_type=op.entity_type,
                        error=error_msg,
                        tenant_id=tenant_id,
                        device_id="batch_processing",
                        retry_count=op.retry_count,
                        will_retry=True,
                    )
                else:
                    # Permanent failure or max retries exceeded
                    op.status = "REJECTED"
                    op.error_message = error_msg
                    failed += 1

                    SyncLogger.log_operation_failed(
                        operation_id=op.id,
                        entity_type=op.entity_type,
                        error=error_msg,
                        tenant_id=tenant_id,
                        device_id="batch_processing",
                        retry_count=op.retry_count,
                        will_retry=False,
                    )

                op.save(update_fields=["status", "error_message", "retry_count"])

        # H-003: If we had transient failures, retry the entire task
        if transient_failures > 0:
            logger.warning(
                f"Encountered {transient_failures} transient failures. "
                f"Retrying task with exponential backoff."
            )
            raise self.retry(
                exc=Exception(f"{transient_failures} transient failures detected"),
                countdown=min(
                    RETRY_BACKOFF_BASE * (2 ** self.request.retries),
                    RETRY_BACKOFF_MAX,
                ),
            )

    except MaxRetriesExceededError:
        logger.error(
            f"Max retries exceeded for sync_pending_operations (tenant={tenant_id}). "
            "Manual intervention may be required."
        )
        raise

    except Exception as e:
        # H-003: Check if this is a transient error worth retrying
        if _is_transient_error(e):
            logger.warning(
                f"Transient error in sync_pending_operations: {e}. "
                f"Retrying (attempt {self.request.retries + 1}/{MAX_RETRY_ATTEMPTS + 1})"
            )
            raise self.retry(
                exc=e,
                countdown=min(
                    RETRY_BACKOFF_BASE * (2 ** self.request.retries),
                    RETRY_BACKOFF_MAX,
                ),
            )
        else:
            # Permanent error - don't retry
            logger.error(
                f"Permanent error in sync_pending_operations: {e}. Not retrying."
            )
            raise

    result = {
        "tenant_id": tenant_id,
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "transient_failures": transient_failures,
        "batch_size": batch_size,
        "retry_attempt": self.request.retries,
    }

    logger.info(f"Sync operation completed: {result}")
    return result


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    rate_limit="20/m",
)
def process_fiscal_queue(self, tenant_id: str) -> dict:
    """
    Process fiscal document queue with retry logic.

    This task handles fiscal document finalization which requires
    external API calls and may need retry logic.

    Args:
        tenant_id: UUID of the tenant

    Returns:
        dict: Summary of processed fiscal documents
    """
    logger.info(f"Processing fiscal queue for tenant {tenant_id}")

    # This would integrate with fiscal document processing
    # For now, return a placeholder result
    result = {
        "tenant_id": tenant_id,
        "documents_processed": 0,
        "documents_pending": 0,
        "status": "completed",
    }

    logger.info(f"Fiscal queue processing completed: {result}")
    return result


@shared_task(
    bind=True,
    max_retries=1,
    rate_limit="5/m",
)
def cleanup_old_sync_sessions(self, days_old: int = 30) -> dict:
    """
    Cleanup old sync session records.

    Args:
        days_old: Delete sessions older than this many days

    Returns:
        dict: Summary of cleanup operation
    """
    from apps.sync.models import SyncSession

    cutoff_date = timezone.now() - timedelta(days=days_old)

    logger.info(f"Cleaning up sync sessions older than {cutoff_date}")

    deleted_count, _ = SyncSession.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    result = {
        "deleted_sessions": deleted_count,
        "cutoff_date": cutoff_date.isoformat(),
    }

    logger.info(f"Sync session cleanup completed: {result}")
    return result


@shared_task(
    bind=True,
    rate_limit="10/m",
)
def retry_failed_operations(self, tenant_id: str, max_retries: int = 3) -> dict:
    """
    Retry failed sync operations that haven't exceeded max retries.

    Args:
        tenant_id: UUID of the tenant
        max_retries: Maximum retry attempts before giving up

    Returns:
        dict: Summary of retry operation
    """
    from apps.sync.models import PendingOperation

    logger.info(f"Retrying failed operations for tenant {tenant_id}")

    # Find failed operations that can be retried
    failed_ops = PendingOperation.objects.filter(
        tenant_id=tenant_id,
        status="REJECTED",
        retry_count__lt=max_retries,
    )

    retried = 0
    for op in failed_ops:
        op.status = "PENDING"
        op.retry_count += 1
        op.save(update_fields=["status", "retry_count"])
        retried += 1

    result = {
        "tenant_id": tenant_id,
        "operations_retried": retried,
    }

    logger.info(f"Retry operation completed: {result}")
    return result
