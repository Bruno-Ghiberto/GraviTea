"""
Unit tests for sync module models.

Tests SyncSession and PendingOperation models for offline-first
synchronization capabilities.
"""

import uuid

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.sync.models import PendingOperation, SyncSession

# ============================================================
# SyncSession Model Tests
# ============================================================


@pytest.mark.django_db
class TestSyncSessionModel:
    """Test SyncSession model functionality."""

    def test_create_sync_session_with_required_fields(self, tenant_context, branch):
        """Test creating a SyncSession with required fields."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-001",
        )

        assert session.id is not None
        assert session.tenant == tenant_context
        assert session.branch == branch
        assert session.device_id == "POS-001"
        assert session.status == SyncSession.SyncStatus.PENDING
        assert session.sync_vector == {}
        assert session.last_sync_at is None
        assert session.error_message is None
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_sync_session_default_status_pending(self, tenant_context, branch):
        """Test SyncSession defaults to PENDING status."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-002",
        )

        assert session.status == SyncSession.SyncStatus.PENDING

    def test_sync_session_status_transitions(self, tenant_context, branch):
        """Test SyncSession status transitions."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-003",
        )

        # PENDING → IN_PROGRESS
        session.status = SyncSession.SyncStatus.IN_PROGRESS
        session.save()
        session.refresh_from_db()
        assert session.status == SyncSession.SyncStatus.IN_PROGRESS

        # IN_PROGRESS → COMPLETED
        session.status = SyncSession.SyncStatus.COMPLETED
        session.last_sync_at = timezone.now()
        session.save()
        session.refresh_from_db()
        assert session.status == SyncSession.SyncStatus.COMPLETED
        assert session.last_sync_at is not None

    def test_sync_session_failed_status_with_error(self, tenant_context, branch):
        """Test SyncSession FAILED status with error message."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-004",
            status=SyncSession.SyncStatus.FAILED,
            error_message="Network timeout during sync",
        )

        assert session.status == SyncSession.SyncStatus.FAILED
        assert session.error_message == "Network timeout during sync"

    def test_sync_session_conflict_status(self, tenant_context, branch):
        """Test SyncSession CONFLICT status for conflict resolution."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-005",
            status=SyncSession.SyncStatus.CONFLICT,
        )

        assert session.status == SyncSession.SyncStatus.CONFLICT

    def test_sync_vector_jsonfield_storage(self, tenant_context, branch):
        """Test sync_vector JSONField can store vector clock data."""
        vector_clock = {
            "device_1": 5,
            "device_2": 3,
            "device_3": 7,
        }

        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-006",
            sync_vector=vector_clock,
        )
        session.refresh_from_db()

        assert session.sync_vector == vector_clock
        assert session.sync_vector["device_1"] == 5
        assert session.sync_vector["device_2"] == 3
        assert session.sync_vector["device_3"] == 7

    def test_sync_vector_default_empty_dict(self, tenant_context, branch):
        """Test sync_vector defaults to empty dict."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-007",
        )

        assert session.sync_vector == {}
        assert isinstance(session.sync_vector, dict)

    def test_sync_vector_complex_structure(self, tenant_context, branch):
        """Test sync_vector can store complex nested structures."""
        complex_vector = {
            "devices": {
                "POS-001": {"timestamp": 1234567890, "version": 1},
                "POS-002": {"timestamp": 1234567891, "version": 2},
            },
            "operations": [
                {"id": "op-1", "status": "completed"},
                {"id": "op-2", "status": "pending"},
            ],
        }

        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-008",
            sync_vector=complex_vector,
        )
        session.refresh_from_db()

        assert session.sync_vector == complex_vector
        assert session.sync_vector["devices"]["POS-001"]["version"] == 1
        assert len(session.sync_vector["operations"]) == 2

    def test_unique_device_id_per_tenant(self, tenant_context, branch):
        """Test device_id must be unique per tenant."""
        from django.db import transaction

        SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-UNIQUE",
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                SyncSession.objects.create(
                    tenant=tenant_context,
                    branch=branch,
                    device_id="POS-UNIQUE",
                )

    def test_same_device_id_different_tenants_allowed(self, tenant_context, other_tenant, branch):
        """Test same device_id is allowed for different tenants."""
        # Create branch for other_tenant
        # Set other tenant context to create branch
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="456 Other St",
            is_active=True,
        )

        # Restore original tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        session1 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-SHARED",
        )

        # Switch to other tenant context
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        session2 = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="POS-SHARED",
        )

        assert session1.device_id == session2.device_id
        assert session1.tenant != session2.tenant

    def test_tenant_bound_manager_filters_by_tenant(self, tenant_context, other_tenant, branch):
        """Test TenantBoundManager filters SyncSession by tenant_id."""
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        # Switch to other tenant context to create branch
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="789 Other Ave",
            is_active=True,
        )

        # Restore tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        session1 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-TENANT-1",
        )

        # Switch to other tenant context
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        session2 = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="POS-TENANT-2",
        )

        # Set tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        # Should only see tenant's sessions
        sessions = SyncSession.objects.all()
        assert sessions.count() == 1
        assert session1 in sessions
        assert session2 not in sessions

        # Clear context and set other_tenant
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        sessions = SyncSession.objects.all()
        assert sessions.count() == 1
        assert session2 in sessions
        assert session1 not in sessions

    def test_last_sync_at_timestamp_updates(self, tenant_context, branch):
        """Test last_sync_at timestamp updates on sync completion."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-TIMESTAMP",
        )

        assert session.last_sync_at is None

        # Update last_sync_at
        sync_time = timezone.now()
        session.last_sync_at = sync_time
        session.status = SyncSession.SyncStatus.COMPLETED
        session.save()
        session.refresh_from_db()

        assert session.last_sync_at is not None
        assert session.last_sync_at == sync_time

    def test_sync_session_str_representation(self, tenant_context, branch):
        """Test SyncSession string representation."""
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-STR",
        )

        expected = f"Sync: POS-STR @ {branch.name}"
        assert str(session) == expected

    def test_sync_session_ordering_by_updated_at(self, tenant_context, branch):
        """Test SyncSession ordering is by -updated_at."""
        session1 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-ORDER-1",
        )

        session2 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-ORDER-2",
        )

        # Update session1 to make it more recent
        session1.status = SyncSession.SyncStatus.COMPLETED
        session1.save()

        set_current_tenant_id(tenant_context.id)
        sessions = list(SyncSession.objects.all())

        # Most recently updated should be first
        assert sessions[0] == session1
        assert sessions[1] == session2

    def test_sync_session_tenant_id_set_on_assignment(self, tenant_context, branch):
        """Test SyncSession tenant_id is set when tenant is assigned."""
        session = SyncSession(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-AUTO-TENANT",
        )

        # Django ForeignKey sets tenant_id immediately upon assignment
        assert session.tenant_id == tenant_context.id

        session.save()

        # Verify it's persisted correctly
        session.refresh_from_db()
        assert session.tenant_id == tenant_context.id


# ============================================================
# PendingOperation Model Tests
# ============================================================


@pytest.mark.django_db
class TestPendingOperationModel:
    """Test PendingOperation model functionality."""

    def test_create_pending_operation_create_type(self, tenant_context, branch):
        """Test creating a PendingOperation with CREATE operation type."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-1",
        )

        entity_id = uuid.uuid4()
        client_ts = timezone.now()

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=entity_id,
            payload={"total": "150.00", "items": []},
            client_timestamp=client_ts,
        )

        assert operation.id is not None
        assert operation.tenant == tenant_context
        assert operation.sync_session == sync_session
        assert operation.operation_type == PendingOperation.OperationType.CREATE
        assert operation.entity_type == "Sale"
        assert operation.entity_id == entity_id
        assert operation.payload == {"total": "150.00", "items": []}
        assert operation.client_timestamp == client_ts
        assert operation.server_timestamp is not None
        assert operation.status == PendingOperation.OperationStatus.PENDING
        assert operation.conflict_data is None
        assert operation.error_message is None
        assert operation.processed_at is None

    def test_create_pending_operation_update_type(self, tenant_context, branch):
        """Test creating a PendingOperation with UPDATE operation type."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-2",
        )

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            payload={"price": "99.99"},
            client_timestamp=timezone.now(),
        )

        assert operation.operation_type == PendingOperation.OperationType.UPDATE

    def test_create_pending_operation_delete_type(self, tenant_context, branch):
        """Test creating a PendingOperation with DELETE operation type."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-3",
        )

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.DELETE,
            entity_type="StockMovement",
            entity_id=uuid.uuid4(),
            payload={"reason": "cancelled"},
            client_timestamp=timezone.now(),
        )

        assert operation.operation_type == PendingOperation.OperationType.DELETE

    def test_pending_operation_default_status_pending(self, tenant_context, branch):
        """Test PendingOperation defaults to PENDING status."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-4",
        )

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
        )

        assert operation.status == PendingOperation.OperationStatus.PENDING

    def test_pending_operation_status_transitions(self, tenant_context, branch):
        """Test PendingOperation status transitions."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-5",
        )

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            payload={"quantity": 10},
            client_timestamp=timezone.now(),
        )

        # PENDING → PROCESSING
        operation.status = PendingOperation.OperationStatus.PROCESSING
        operation.save()
        operation.refresh_from_db()
        assert operation.status == PendingOperation.OperationStatus.PROCESSING

        # PROCESSING → APPLIED
        operation.status = PendingOperation.OperationStatus.APPLIED
        operation.processed_at = timezone.now()
        operation.save()
        operation.refresh_from_db()
        assert operation.status == PendingOperation.OperationStatus.APPLIED
        assert operation.processed_at is not None

    def test_pending_operation_rejected_status(self, tenant_context, branch):
        """Test PendingOperation REJECTED status."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-6",
        )

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
            status=PendingOperation.OperationStatus.REJECTED,
            error_message="Invalid payload structure",
        )

        assert operation.status == PendingOperation.OperationStatus.REJECTED
        assert operation.error_message == "Invalid payload structure"

    def test_pending_operation_conflict_status(self, tenant_context, branch):
        """Test PendingOperation CONFLICT status with conflict_data."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-7",
        )

        conflict_info = {
            "client_version": 1,
            "server_version": 2,
            "conflicting_fields": ["quantity"],
        }

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            payload={"quantity": 5},
            client_timestamp=timezone.now(),
            status=PendingOperation.OperationStatus.CONFLICT,
            conflict_data=conflict_info,
        )

        assert operation.status == PendingOperation.OperationStatus.CONFLICT
        assert operation.conflict_data == conflict_info
        assert operation.conflict_data["client_version"] == 1

    def test_payload_jsonfield_validation(self, tenant_context, branch):
        """Test payload JSONField can store complex operation data."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-8",
        )

        complex_payload = {
            "sale": {
                "total": "250.50",
                "subtotal": "207.02",
                "tax": "43.48",
                "items": [
                    {"product_id": str(uuid.uuid4()), "quantity": 2, "price": "50.00"},
                    {"product_id": str(uuid.uuid4()), "quantity": 1, "price": "107.02"},
                ],
                "customer": {
                    "id": str(uuid.uuid4()),
                    "name": "John Doe",
                },
                "metadata": {
                    "created_offline": True,
                    "device_version": "1.2.3",
                },
            }
        }

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload=complex_payload,
            client_timestamp=timezone.now(),
        )
        operation.refresh_from_db()

        assert operation.payload == complex_payload
        assert operation.payload["sale"]["total"] == "250.50"
        assert len(operation.payload["sale"]["items"]) == 2
        assert operation.payload["sale"]["metadata"]["created_offline"] is True

    def test_client_timestamp_vs_server_timestamp(self, tenant_context, branch):
        """Test client_timestamp and server_timestamp are distinct."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-9",
        )

        # Client timestamp is in the past
        client_ts = timezone.now() - timezone.timedelta(hours=2)

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=client_ts,
        )

        assert operation.client_timestamp == client_ts
        assert operation.server_timestamp > operation.client_timestamp

    def test_ordering_by_client_timestamp(self, tenant_context, branch):
        """Test PendingOperation ordering is by client_timestamp."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-10",
        )

        base_time = timezone.now()

        op1 = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=base_time + timezone.timedelta(seconds=2),
        )

        op2 = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=base_time + timezone.timedelta(seconds=1),
        )

        op3 = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=base_time,
        )

        set_current_tenant_id(tenant_context.id)
        operations = list(PendingOperation.objects.all())

        # Should be ordered by client_timestamp ascending
        assert operations[0] == op3
        assert operations[1] == op2
        assert operations[2] == op1

    def test_entity_type_and_entity_id_indexing(self, tenant_context, branch):
        """Test entity_type and entity_id are properly indexed."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-11",
        )

        product_id = uuid.uuid4()

        op1 = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Product",
            entity_id=product_id,
            payload={"name": "Test Product"},
            client_timestamp=timezone.now(),
        )

        op2 = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Product",
            entity_id=product_id,
            payload={"name": "Updated Product"},
            client_timestamp=timezone.now(),
        )

        set_current_tenant_id(tenant_context.id)

        # Query by entity_type and entity_id
        product_ops = PendingOperation.objects.filter(
            entity_type="Product",
            entity_id=product_id,
        )

        assert product_ops.count() == 2
        assert op1 in product_ops
        assert op2 in product_ops

    def test_conflict_data_storage(self, tenant_context, branch):
        """Test conflict_data JSONField storage."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-12",
        )

        conflict_data = {
            "resolution_strategy": "server_wins",
            "client_data": {"quantity": 5},
            "server_data": {"quantity": 10},
            "timestamp": timezone.now().isoformat(),
        }

        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            payload={"quantity": 5},
            client_timestamp=timezone.now(),
            conflict_data=conflict_data,
        )
        operation.refresh_from_db()

        assert operation.conflict_data == conflict_data
        assert operation.conflict_data["resolution_strategy"] == "server_wins"
        assert operation.conflict_data["client_data"]["quantity"] == 5

    def test_tenant_bound_manager_filters_operations(self, tenant_context, other_tenant, branch):
        """Test TenantBoundManager filters PendingOperation by tenant_id."""
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        # Switch to other tenant context to create branch
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="999 Other St",
            is_active=True,
        )

        # Restore tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        session1 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-TENANT-OP-1",
        )

        # Switch to other tenant context
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        session2 = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="POS-TENANT-OP-2",
        )

        # Switch back to tenant_context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        op1 = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=session1,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
        )

        # Switch to other tenant
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        op2 = PendingOperation.objects.create(
            tenant=other_tenant,
            sync_session=session2,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
        )

        # Set tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        operations = PendingOperation.objects.all()
        assert operations.count() == 1
        assert op1 in operations
        assert op2 not in operations

        # Switch to other_tenant
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        operations = PendingOperation.objects.all()
        assert operations.count() == 1
        assert op2 in operations
        assert op1 not in operations

    def test_pending_operation_str_representation(self, tenant_context, branch):
        """Test PendingOperation string representation."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OP-STR",
        )

        entity_id = uuid.uuid4()
        operation = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Product",
            entity_id=entity_id,
            payload={},
            client_timestamp=timezone.now(),
        )

        expected = f"UPDATE Product:{entity_id}"
        assert str(operation) == expected

    def test_pending_operation_tenant_id_set_on_assignment(self, tenant_context, branch):
        """Test PendingOperation tenant_id is set when tenant is assigned."""
        sync_session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-AUTO-OP",
        )

        operation = PendingOperation(
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
        )

        # Django ForeignKey sets tenant_id immediately upon assignment
        assert operation.tenant_id == tenant_context.id

        operation.save()

        # Verify it's persisted correctly
        operation.refresh_from_db()
        assert operation.tenant_id == tenant_context.id


# ============================================================
# Integration Tests - Tenant Isolation and IDOR Prevention
# ============================================================


@pytest.mark.django_db
class TestTenantIsolationIntegration:
    """Test tenant isolation and IDOR prevention."""

    def test_tenant_isolation_sync_sessions(self, tenant_context, other_tenant, branch):
        """Test SyncSession tenant isolation prevents cross-tenant access."""
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        # Switch to other tenant to create branch
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="123 Other Ave",
            is_active=True,
        )

        # Restore tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        # Create sessions for both tenants
        session_tenant_a = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-ISOLATED-A",
        )

        # Switch to other tenant
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        session_tenant_b = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="POS-ISOLATED-B",
        )

        # Set tenant A context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        # Tenant A should only see their sessions
        sessions = SyncSession.objects.all()
        assert sessions.count() == 1
        assert session_tenant_a in sessions
        assert session_tenant_b not in sessions

        # Cannot access tenant B session by ID
        with pytest.raises(SyncSession.DoesNotExist):
            SyncSession.objects.get(id=session_tenant_b.id)

    def test_tenant_isolation_pending_operations(self, tenant_context, other_tenant, branch):
        """Test PendingOperation tenant isolation prevents cross-tenant access."""
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        # Switch to other tenant to create branch
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="456 Other Ave",
            is_active=True,
        )

        # Restore tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        session_a = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-A",
        )

        # Switch to other tenant
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        session_b = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="POS-B",
        )

        # Switch back to tenant_context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        op_a = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=session_a,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
        )

        # Switch to other tenant
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        op_b = PendingOperation.objects.create(
            tenant=other_tenant,
            sync_session=session_b,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=uuid.uuid4(),
            payload={},
            client_timestamp=timezone.now(),
        )

        # Set tenant A context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        # Tenant A should only see their operations
        operations = PendingOperation.objects.all()
        assert operations.count() == 1
        assert op_a in operations
        assert op_b not in operations

    def test_idor_prevention_sync_session_branch(self, tenant_context, other_tenant):
        """Test IDOR prevention: cannot reference branch from different tenant."""
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        # Switch to other tenant to create branch
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        # Create branch for other_tenant
        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="789 Other Ave",
            is_active=True,
        )

        # Restore tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        # Try to create SyncSession for tenant A with branch from tenant B
        # This should fail with ValueError due to IDOR prevention
        with pytest.raises(ValueError, match="IDOR violation"):
            SyncSession.objects.create(
                tenant=tenant_context,
                branch=other_branch,  # Branch belongs to other_tenant!
                device_id="POS-IDOR",
            )

    def test_idor_prevention_pending_operation_sync_session(
        self, tenant_context, other_tenant, branch
    ):
        """Test IDOR prevention: cannot reference sync_session from different tenant."""
        from apps.core.managers.tenant_bound import clear_current_tenant_id
        from apps.core.models import Branch

        # Switch to other tenant to create branch and session
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)

        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            address="999 Other Ave",
            is_active=True,
        )

        # Create sync session for other_tenant
        other_session = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="POS-OTHER",
        )

        # Restore tenant context
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)

        # Try to create PendingOperation for tenant A with sync_session from tenant B
        # This should fail with ValueError due to IDOR prevention
        with pytest.raises(ValueError, match="IDOR violation"):
            PendingOperation.objects.create(
                tenant=tenant_context,
                sync_session=other_session,  # Session belongs to other_tenant!
                operation_type=PendingOperation.OperationType.CREATE,
                entity_type="Sale",
                entity_id=uuid.uuid4(),
                payload={},
                client_timestamp=timezone.now(),
            )
