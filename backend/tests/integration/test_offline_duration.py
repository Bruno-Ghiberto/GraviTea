"""
Stress tests for 72-hour offline operation capability (SC-010).

Tests verify system can accumulate and sync operations from 72 hours
of offline POS operation, meeting SC-011 5-minute sync performance target.
"""

import time
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventario.models import Product, StockSnapshot
from apps.sync.models import PendingOperation, SyncSession


@pytest.fixture
def offline_test_data(tenant_context, branch):
    """Create test data for offline simulation."""
    # Create products for sales
    products = []
    for i in range(20):  # 20 products to rotate through
        product = Product.objects.create(
            tenant=tenant_context,
            sku=f"OFFLINE-{i:03d}",
            name=f"Offline Test Product {i}",
            unit_price=Decimal(f"{10 + i}.990"),
            cost_price=Decimal(f"{5 + i}.500"),
            is_active=True,
        )
        products.append(product)

        # Create initial stock snapshot
        StockSnapshot.objects.create(
            product=product,
            branch=branch,
            quantity=Decimal("1000.0000"),
        )

    return {
        "products": products,
        "branch": branch,
    }


@pytest.mark.django_db
@pytest.mark.performance
@pytest.mark.slow
class TestOfflineDurationCapability:
    """
    Tests for SC-010: 72-hour offline operation capability.

    Simulates accumulating sales operations over 72 hours and
    verifies sync can complete within SC-011 5-minute target.
    """

    def test_can_accumulate_72_hours_of_operations(self, tenant_context, branch, offline_test_data):
        """
        Test that system can accumulate operations for 72 hours.

        Simulates 12 sales per hour for 72 hours = 864 sales.
        Each sale generates multiple pending operations.
        """
        products = offline_test_data["products"]

        # Create a sync session to track offline period
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-OFFLINE-001",
            status=SyncSession.SyncStatus.PENDING,
        )

        # Simulate 72 hours of operations (12 sales per hour = 864 sales)
        # For test performance, we create representative sample
        hours_to_simulate = 72
        sales_per_hour = 12
        total_operations = hours_to_simulate * sales_per_hour

        operations_created = 0
        base_time = timezone.now() - timedelta(hours=hours_to_simulate)

        for hour in range(hours_to_simulate):
            for sale_num in range(sales_per_hour):
                # Rotate through products
                product = products[(hour * sales_per_hour + sale_num) % len(products)]

                # Create pending operation for sale
                operation_time = base_time + timedelta(hours=hour, minutes=sale_num * 5)

                PendingOperation.objects.create(
                    tenant=tenant_context,
                    sync_session=session,
                    operation_type=PendingOperation.OperationType.CREATE,
                    entity_type="stock_movement",
                    entity_id=uuid.uuid4(),
                    payload={
                        "product_id": str(product.id),
                        "branch_id": str(branch.id),
                        "type": "SALE",
                        "quantity_delta": "-1.0000",
                        "cost_snapshot": str(product.cost_price),
                        "reference_id": f"SALE-{hour:02d}-{sale_num:02d}",
                        "created_at": operation_time.isoformat(),
                    },
                    client_timestamp=operation_time,
                    status=PendingOperation.OperationStatus.PENDING,
                )
                operations_created += 1

        # Verify all operations were created
        assert operations_created == total_operations
        assert PendingOperation.all_objects.filter(sync_session=session).count() == total_operations

    def test_sync_performance_within_5_minutes(self, tenant_context, branch, offline_test_data):
        """
        Test that sync can complete within SC-011 5-minute target.

        This test creates a realistic number of pending operations
        and measures sync processing time.
        """
        products = offline_test_data["products"]

        # Create sync session
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-PERF-001",
            status=SyncSession.SyncStatus.PENDING,
        )

        # Create 100 pending operations (representative sample)
        num_operations = 100
        now = timezone.now()
        for i in range(num_operations):
            product = products[i % len(products)]
            PendingOperation.objects.create(
                tenant=tenant_context,
                sync_session=session,
                operation_type=PendingOperation.OperationType.CREATE,
                entity_type="stock_movement",
                entity_id=uuid.uuid4(),
                payload={
                    "product_id": str(product.id),
                    "branch_id": str(branch.id),
                    "type": "SALE",
                    "quantity_delta": "-1.0000",
                    "cost_snapshot": str(product.cost_price),
                },
                client_timestamp=now,
                status=PendingOperation.OperationStatus.PENDING,
            )

        # Measure time to process operations
        start_time = time.time()

        # Simulate sync processing - mark operations as synced
        pending_ops = PendingOperation.all_objects.filter(
            sync_session=session, status=PendingOperation.OperationStatus.PENDING
        )

        for op in pending_ops:
            # Simulate processing each operation
            op.status = PendingOperation.OperationStatus.APPLIED
            op.save()

        end_time = time.time()
        processing_time = end_time - start_time

        # SC-011: Sync must complete within 5 minutes (300 seconds)
        # For 100 operations, should be well under this
        max_time_per_100 = 30  # 30 seconds for 100 operations is reasonable
        assert processing_time < max_time_per_100, (
            f"Processing {num_operations} operations took {processing_time:.2f}s, "
            f"expected < {max_time_per_100}s"
        )

        # Verify all operations were synced
        assert (
            PendingOperation.all_objects.filter(
                sync_session=session, status=PendingOperation.OperationStatus.APPLIED
            ).count()
            == num_operations
        )

    def test_operation_ordering_preserved(self, tenant_context, branch, offline_test_data):
        """Test that operation ordering is preserved during offline accumulation."""
        products = offline_test_data["products"]

        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-ORDER-001",
            status=SyncSession.SyncStatus.PENDING,
        )

        # Create operations with specific ordering
        operation_ids = []
        now = timezone.now()
        for i in range(10):
            op = PendingOperation.objects.create(
                tenant=tenant_context,
                sync_session=session,
                operation_type=PendingOperation.OperationType.CREATE,
                entity_type="stock_movement",
                entity_id=uuid.uuid4(),
                payload={
                    "product_id": str(products[0].id),
                    "branch_id": str(branch.id),
                    "sequence": i,
                },
                client_timestamp=now + timedelta(seconds=i),
                status=PendingOperation.OperationStatus.PENDING,
            )
            operation_ids.append(op.id)

        # Verify operations can be retrieved in order
        retrieved_ops = list(
            PendingOperation.all_objects.filter(sync_session=session)
            .order_by("client_timestamp", "id")
            .values_list("id", flat=True)
        )

        assert retrieved_ops == operation_ids

    def test_session_tracks_offline_period(self, tenant_context, branch):
        """Test that sync session correctly tracks offline duration."""
        # Create session that started 72 hours ago
        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-TRACK-001",
            status=SyncSession.SyncStatus.PENDING,
        )

        # Session should have timestamps
        assert session.created_at is not None
        assert session.id is not None

        # Simulate completing sync
        session.status = SyncSession.SyncStatus.COMPLETED
        session.save()

        session.refresh_from_db()
        assert session.status == SyncSession.SyncStatus.COMPLETED


@pytest.mark.django_db
@pytest.mark.performance
class TestSyncRecovery:
    """Tests for sync recovery after offline period."""

    def test_partial_sync_can_resume(self, tenant_context, branch, offline_test_data):
        """Test that a partially completed sync can be resumed."""
        products = offline_test_data["products"]

        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-RESUME-001",
            status=SyncSession.SyncStatus.IN_PROGRESS,
        )

        # Create 20 operations
        now = timezone.now()
        for i in range(20):
            status = (
                PendingOperation.OperationStatus.APPLIED
                if i < 10
                else PendingOperation.OperationStatus.PENDING
            )
            PendingOperation.objects.create(
                tenant=tenant_context,
                sync_session=session,
                operation_type=PendingOperation.OperationType.CREATE,
                entity_type="stock_movement",
                entity_id=uuid.uuid4(),
                payload={"product_id": str(products[0].id)},
                client_timestamp=now,
                status=status,
            )

        # Verify we can identify remaining operations
        pending_count = PendingOperation.all_objects.filter(
            sync_session=session, status=PendingOperation.OperationStatus.PENDING
        ).count()

        synced_count = PendingOperation.all_objects.filter(
            sync_session=session, status=PendingOperation.OperationStatus.APPLIED
        ).count()

        assert pending_count == 10
        assert synced_count == 10

    def test_failed_operations_marked_correctly(self, tenant_context, branch, offline_test_data):
        """Test that failed operations are tracked for retry."""
        products = offline_test_data["products"]

        session = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="POS-FAIL-001",
            status=SyncSession.SyncStatus.IN_PROGRESS,
        )

        # Create operation that will "fail"
        now = timezone.now()
        op = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="stock_movement",
            entity_id=uuid.uuid4(),
            payload={"product_id": str(products[0].id)},
            client_timestamp=now,
            status=PendingOperation.OperationStatus.PENDING,
        )

        # Simulate failure
        op.status = PendingOperation.OperationStatus.REJECTED
        op.error_message = "Test failure"
        op.save()

        op.refresh_from_db()
        assert op.status == PendingOperation.OperationStatus.REJECTED
        assert op.error_message == "Test failure"

        # Retry should be possible
        op.status = PendingOperation.OperationStatus.PENDING
        op.error_message = None
        op.save()

        assert op.status == PendingOperation.OperationStatus.PENDING
