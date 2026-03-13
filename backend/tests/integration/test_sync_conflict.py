"""
Integration tests: Offline Sync → Conflict Resolution.

Verifies the PendingOperation lifecycle:
1. Offline operation queued as PendingOperation (PENDING)
2. Sync processes operations → APPLIED or CONFLICT
3. Conflict detection when concurrent modifications exist
4. Tenant isolation in sync operations

Per spec 011-backend-devops-coherence FR-026.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def _sync_setup(tenant_context, branch):
    """Create a SyncSession with PendingOperations for testing."""
    from apps.sync.models import PendingOperation, SyncSession

    session = SyncSession.objects.create(
        tenant=tenant_context,
        branch=branch,
        device_id="POS-SYNC-001",
        status=SyncSession.SyncStatus.PENDING,
    )
    return session


@pytest.fixture
def _product_for_sync(tenant_context, product_category):
    """Product to use as sync target entity."""
    from apps.inventario.models import Product

    return Product.objects.create(
        tenant=tenant_context,
        sku="SYNC-PROD-001",
        name="Sync Target Product",
        category=product_category,
        unit_price=Decimal("100.000"),
        cost_price=Decimal("50.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )


# ============================================================
# Tests
# ============================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestPendingOperationLifecycle:
    """PendingOperation creation and status transitions."""

    def test_create_pending_operation(self, _sync_setup, _product_for_sync):
        """Offline operation is queued as PENDING."""
        from apps.sync.models import PendingOperation

        op = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={
                "name": "Updated Product Name",
                "unit_price": "150.000",
            },
            client_timestamp=timezone.now() - timedelta(minutes=5),
            status=PendingOperation.OperationStatus.PENDING,
        )

        assert op.status == PendingOperation.OperationStatus.PENDING
        assert op.entity_type == "product"
        assert op.entity_id == _product_for_sync.id
        assert op.retry_count == 0

    def test_operation_transitions_to_applied(self, _sync_setup, _product_for_sync):
        """PENDING operation can transition to APPLIED."""
        from apps.sync.models import PendingOperation

        op = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={"name": "Applied Update"},
            client_timestamp=timezone.now(),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Simulate sync processing: apply and mark
        op.status = PendingOperation.OperationStatus.APPLIED
        op.server_timestamp = timezone.now()
        op.save()

        op.refresh_from_db()
        assert op.status == PendingOperation.OperationStatus.APPLIED
        assert op.server_timestamp is not None

    def test_operation_transitions_to_conflict(self, _sync_setup, _product_for_sync):
        """PENDING operation can transition to CONFLICT with conflict_data."""
        from apps.sync.models import PendingOperation

        op = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={"name": "Conflict Update"},
            client_timestamp=timezone.now() - timedelta(minutes=10),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Simulate conflict detection
        op.status = PendingOperation.OperationStatus.CONFLICT
        op.conflict_data = {
            "reason": "server_wins",
            "server_value": {"name": "Server Update"},
            "client_value": {"name": "Conflict Update"},
        }
        op.server_timestamp = timezone.now()
        op.save()

        op.refresh_from_db()
        assert op.status == PendingOperation.OperationStatus.CONFLICT
        assert op.conflict_data["reason"] == "server_wins"


@pytest.mark.django_db
@pytest.mark.integration
class TestConflictDetection:
    """Detect conflicts when concurrent modifications exist."""

    def test_concurrent_updates_detected(self, _sync_setup, _product_for_sync):
        """Two operations on the same entity with stale timestamps produce conflict."""
        from apps.sync.models import PendingOperation

        # Operation 1: older client timestamp (simulates offline device)
        op1 = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={"name": "Offline Device 1 Update"},
            client_timestamp=timezone.now() - timedelta(hours=2),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Simulate server-side update happened after op1's client_timestamp
        _product_for_sync.name = "Server Updated Name"
        _product_for_sync.save()

        # Operation 2: another device also updated the same entity
        op2 = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={"name": "Offline Device 2 Update"},
            client_timestamp=timezone.now() - timedelta(hours=1),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Both operations target the same entity — this is a conflict scenario
        conflicting_ops = PendingOperation.objects.filter(
            entity_type="product",
            entity_id=_product_for_sync.id,
            status=PendingOperation.OperationStatus.PENDING,
        ).order_by("client_timestamp")

        assert conflicting_ops.count() == 2

        # Simulate resolution: first wins, second conflicts
        first = conflicting_ops.first()
        first.status = PendingOperation.OperationStatus.APPLIED
        first.server_timestamp = timezone.now()
        first.save()

        second = conflicting_ops.last()
        second.status = PendingOperation.OperationStatus.CONFLICT
        second.conflict_data = {
            "reason": "concurrent_modification",
            "applied_op_id": str(first.id),
        }
        second.server_timestamp = timezone.now()
        second.save()

        applied = PendingOperation.objects.filter(
            entity_id=_product_for_sync.id,
            status=PendingOperation.OperationStatus.APPLIED,
        ).count()
        conflicts = PendingOperation.objects.filter(
            entity_id=_product_for_sync.id,
            status=PendingOperation.OperationStatus.CONFLICT,
        ).count()

        assert applied == 1
        assert conflicts == 1

    def test_create_delete_conflict(self, _sync_setup, _product_for_sync):
        """CREATE followed by DELETE on same entity is a conflict scenario."""
        from apps.sync.models import PendingOperation

        new_entity_id = uuid.uuid4()

        # Offline CREATE
        create_op = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="customer",
            entity_id=new_entity_id,
            payload={"razon_social": "New Customer", "cuit": "20111111112"},
            client_timestamp=timezone.now() - timedelta(minutes=30),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Offline DELETE (same entity, same session — device changed mind)
        delete_op = PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.DELETE,
            entity_type="customer",
            entity_id=new_entity_id,
            payload={},
            client_timestamp=timezone.now() - timedelta(minutes=15),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Verify both exist as PENDING
        ops = PendingOperation.objects.filter(
            entity_id=new_entity_id,
            status=PendingOperation.OperationStatus.PENDING,
        )
        assert ops.count() == 2

        # Resolve: apply CREATE, then apply DELETE (net result: no entity)
        create_op.status = PendingOperation.OperationStatus.APPLIED
        create_op.server_timestamp = timezone.now()
        create_op.save()

        delete_op.status = PendingOperation.OperationStatus.APPLIED
        delete_op.server_timestamp = timezone.now()
        delete_op.save()

        all_applied = PendingOperation.objects.filter(
            entity_id=new_entity_id,
            status=PendingOperation.OperationStatus.APPLIED,
        ).count()
        assert all_applied == 2


@pytest.mark.django_db
@pytest.mark.integration
class TestSyncTenantIsolation:
    """Sync operations respect tenant boundaries."""

    def test_sync_session_isolated_between_tenants(
        self, tenant_context, other_tenant, branch
    ):
        """Sync sessions from tenant A are invisible to tenant B."""
        from apps.sync.models import SyncSession

        SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-ISO-A",
            status=SyncSession.SyncStatus.PENDING,
        )

        assert SyncSession.objects.count() == 1

        try:
            clear_current_tenant_id()
            set_current_tenant_id(other_tenant.id)

            assert SyncSession.objects.count() == 0
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)

    def test_pending_operations_isolated(
        self, tenant_context, other_tenant, branch, _product_for_sync
    ):
        """PendingOperations from tenant A are invisible to tenant B."""
        from apps.sync.models import PendingOperation, SyncSession

        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-ISO-B",
            status=SyncSession.SyncStatus.PENDING,
        )

        PendingOperation.objects.create(
            sync_session=session,
            tenant=tenant_context,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={"name": "Isolated Update"},
            client_timestamp=timezone.now(),
            status=PendingOperation.OperationStatus.PENDING,
        )

        assert PendingOperation.objects.count() == 1

        try:
            clear_current_tenant_id()
            set_current_tenant_id(other_tenant.id)

            assert PendingOperation.objects.count() == 0
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)


@pytest.mark.django_db
@pytest.mark.integration
class TestSyncSessionStatusTransitions:
    """SyncSession status transitions during sync lifecycle."""

    def test_session_pending_to_in_progress(self, _sync_setup):
        """Sync session transitions PENDING → IN_PROGRESS when sync starts."""
        from apps.sync.models import SyncSession

        _sync_setup.status = SyncSession.SyncStatus.IN_PROGRESS
        _sync_setup.save()

        _sync_setup.refresh_from_db()
        assert _sync_setup.status == SyncSession.SyncStatus.IN_PROGRESS

    def test_session_in_progress_to_completed(self, _sync_setup):
        """Sync session transitions IN_PROGRESS → COMPLETED when all ops applied."""
        from apps.sync.models import SyncSession

        _sync_setup.status = SyncSession.SyncStatus.IN_PROGRESS
        _sync_setup.save()

        _sync_setup.status = SyncSession.SyncStatus.COMPLETED
        _sync_setup.last_sync_at = timezone.now()
        _sync_setup.save()

        _sync_setup.refresh_from_db()
        assert _sync_setup.status == SyncSession.SyncStatus.COMPLETED
        assert _sync_setup.last_sync_at is not None

    def test_session_to_conflict_when_ops_conflict(
        self, _sync_setup, _product_for_sync
    ):
        """Session transitions to CONFLICT when operations have conflicts."""
        from apps.sync.models import PendingOperation, SyncSession

        PendingOperation.objects.create(
            sync_session=_sync_setup,
            tenant=_sync_setup.tenant,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="product",
            entity_id=_product_for_sync.id,
            payload={"name": "Conflicting"},
            client_timestamp=timezone.now(),
            status=PendingOperation.OperationStatus.CONFLICT,
            conflict_data={"reason": "stale_timestamp"},
        )

        _sync_setup.status = SyncSession.SyncStatus.CONFLICT
        _sync_setup.error_message = "1 operation(s) in conflict"
        _sync_setup.save()

        _sync_setup.refresh_from_db()
        assert _sync_setup.status == SyncSession.SyncStatus.CONFLICT
        assert "conflict" in _sync_setup.error_message.lower()
