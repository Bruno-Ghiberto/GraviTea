"""
Sync models for Gravitea ERP.

Provides models for offline-first POS synchronization.
"""

import uuid

from django.db import models

from apps.core.fields import (OPERATION_STATUS_ENUM, OPERATION_TYPE_ENUM,
                              SYNC_STATUS_ENUM, PostgresEnumField)
from apps.core.managers.tenant_bound import (AllObjectsManager,
                                             TenantBoundManager)
from apps.core.models.branch import Branch
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class SyncSession(TenantBoundModel):
    """
    Synchronization session for a POS terminal.

    Tracks sync state and conflict resolution for offline-first operations.

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        branch: Branch the POS terminal belongs to
        device_id: Unique identifier for the POS terminal
        last_sync_at: Timestamp of last successful sync
        sync_vector: JSON containing sync state (vector clock)
        status: Current sync status
        created_at: Session creation timestamp
        updated_at: Last update timestamp
    """

    class SyncStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CONFLICT = "CONFLICT", "Conflict Resolution Required"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="sync_sessions",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="sync_sessions",
        help_text="Branch the POS terminal belongs to",
    )
    device_id = models.CharField(
        max_length=100, db_index=True, help_text="Unique identifier for the POS terminal"
    )
    last_sync_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of last successful sync"
    )
    sync_vector = models.JSONField(default=dict, help_text="Vector clock for sync state tracking")
    status = PostgresEnumField(
        enum_type=SYNC_STATUS_ENUM,
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        db_index=True,
        help_text="Current sync status (PostgreSQL ENUM)",
    )
    error_message = models.TextField(
        null=True, blank=True, help_text="Error details if sync failed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "sync_session"
        ordering = ["-updated_at"]
        verbose_name = "Sync Session"
        verbose_name_plural = "Sync Sessions"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "device_id"], name="unique_device_per_tenant"
            ),
        ]

    def __str__(self):
        return f"Sync: {self.device_id} @ {self.branch.name}"

    def save(self, *args, **kwargs):
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        super().save(*args, **kwargs)


class PendingOperation(TenantBoundModel):
    """
    Pending operation from offline POS terminal.

    Stores operations created offline for later sync and conflict resolution.

    Attributes:
        id: UUID primary key (client-generated for idempotency)
        tenant_id: Parent tenant (via TenantBoundModel)
        sync_session: Associated sync session
        operation_type: Type of operation (CREATE, UPDATE, DELETE)
        entity_type: Type of entity affected (Sale, StockMovement, etc.)
        entity_id: UUID of the affected entity
        payload: JSON containing operation data
        client_timestamp: Timestamp from client device
        server_timestamp: Timestamp when received by server
        status: Processing status
        conflict_data: Conflict resolution data if applicable
    """

    class OperationType(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    class OperationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        APPLIED = "APPLIED", "Applied"
        REJECTED = "REJECTED", "Rejected"
        CONFLICT = "CONFLICT", "Conflict"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Client-generated UUID for idempotency",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="pending_operations",
    )
    sync_session = models.ForeignKey(
        SyncSession,
        on_delete=models.CASCADE,
        related_name="pending_operations",
        db_column="sync_session_id",
        help_text="Associated sync session",
    )
    operation_type = PostgresEnumField(
        enum_type=OPERATION_TYPE_ENUM,
        max_length=10,
        choices=OperationType.choices,
        help_text="Type of operation (PostgreSQL ENUM)",
    )
    entity_type = models.CharField(
        max_length=50, db_index=True, help_text="Type of entity (Sale, StockMovement, etc.)"
    )
    entity_id = models.UUIDField(db_index=True, help_text="UUID of the affected entity")
    payload = models.JSONField(help_text="Operation data as JSON")
    client_timestamp = models.DateTimeField(help_text="Timestamp from client device")
    server_timestamp = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when received by server"
    )
    status = PostgresEnumField(
        enum_type=OPERATION_STATUS_ENUM,
        max_length=20,
        choices=OperationStatus.choices,
        default=OperationStatus.PENDING,
        db_index=True,
        help_text="Processing status (PostgreSQL ENUM)",
    )
    conflict_data = models.JSONField(
        null=True, blank=True, help_text="Conflict resolution data if applicable"
    )
    error_message = models.TextField(
        null=True, blank=True, help_text="Error details if operation failed"
    )
    processed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when operation was processed"
    )
    retry_count = models.PositiveSmallIntegerField(
        default=0, help_text="Number of retry attempts for failed operations"
    )

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "pending_operation"
        ordering = ["client_timestamp"]
        verbose_name = "Pending Operation"
        verbose_name_plural = "Pending Operations"
        indexes = [
            models.Index(
                fields=["tenant_id", "status", "client_timestamp"], name="idx_pending_op_status"
            ),
            models.Index(
                fields=["tenant_id", "entity_type", "entity_id"], name="idx_pending_op_entity"
            ),
            # Partial index for pending operations - optimizes sync queue processing
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_pending_op_queue",
                condition=models.Q(status="PENDING"),
            ),
        ]

    def __str__(self):
        return f"{self.operation_type} {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        super().save(*args, **kwargs)
