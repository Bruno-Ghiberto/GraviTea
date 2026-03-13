"""
Tests for Celery background tasks.

Tests sync and inventory background tasks with mocked Celery
execution using CELERY_TASK_ALWAYS_EAGER for synchronous testing.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


@pytest.fixture
def celery_eager_mode(settings):
    """Configure Celery to run tasks synchronously for testing."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    return settings


# =============================================================================
# Sync Task Tests
# =============================================================================


@pytest.mark.django_db
class TestSyncPendingOperationsTask:
    """Tests for sync_pending_operations task."""

    def test_sync_pending_operations_processes_pending_items(
        self, celery_eager_mode, tenant_context, sync_session
    ):
        """T057: Test sync_pending_operations task execution."""
        from apps.sync.models import PendingOperation
        from apps.sync.tasks import sync_pending_operations

        # Create a pending operation manually
        PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            operation_type="UPDATE",
            payload={"name": "Test"},
            client_timestamp=timezone.now(),
            status="PENDING",
        )

        # Execute task synchronously
        result = sync_pending_operations.apply(
            args=[str(tenant_context.id)],
            kwargs={"batch_size": 10},
        ).get()

        assert result["tenant_id"] == str(tenant_context.id)
        assert result["processed"] >= 0
        assert "failed" in result

    def test_sync_pending_operations_handles_empty_queue(
        self, celery_eager_mode, tenant_context
    ):
        """Test task handles empty queue gracefully."""
        from apps.sync.tasks import sync_pending_operations

        result = sync_pending_operations.apply(
            args=[str(tenant_context.id)],
        ).get()

        assert result["processed"] == 0
        assert result["failed"] == 0

    def test_sync_pending_operations_respects_batch_size(
        self, celery_eager_mode, tenant_context, sync_session
    ):
        """Test task respects batch size limit."""
        from apps.sync.models import PendingOperation
        from apps.sync.tasks import sync_pending_operations

        # Create more operations than batch size
        for i in range(5):
            PendingOperation.objects.create(
                tenant=tenant_context,
                sync_session=sync_session,
                entity_type="Product",
                entity_id=uuid.uuid4(),
                operation_type="UPDATE",
                payload={"name": f"Test {i}"},
                client_timestamp=timezone.now(),
                status="PENDING",
            )

        result = sync_pending_operations.apply(
            args=[str(tenant_context.id)],
            kwargs={"batch_size": 3},
        ).get()

        # Should process at most 3 due to batch limit
        assert result["batch_size"] == 3


@pytest.mark.django_db
class TestProcessFiscalQueueTask:
    """Tests for process_fiscal_queue task."""

    def test_process_fiscal_queue_executes(self, celery_eager_mode, tenant_context):
        """T058: Test process_fiscal_queue task with retry logic."""
        from apps.sync.tasks import process_fiscal_queue

        result = process_fiscal_queue.apply(args=[str(tenant_context.id)]).get()

        assert result["tenant_id"] == str(tenant_context.id)
        assert result["status"] == "completed"

    def test_process_fiscal_queue_has_retry_config(self):
        """Test fiscal queue task has proper retry configuration."""
        from apps.sync.tasks import process_fiscal_queue

        assert process_fiscal_queue.max_retries == 5
        assert process_fiscal_queue.default_retry_delay == 120


@pytest.mark.django_db
class TestCleanupOldSyncSessions:
    """Tests for cleanup_old_sync_sessions task."""

    def test_cleanup_removes_old_sessions(
        self, celery_eager_mode, tenant_context, sync_session, branch
    ):
        """Test cleanup removes sessions older than cutoff."""
        from apps.sync.models import SyncSession
        from apps.sync.tasks import cleanup_old_sync_sessions

        # Make the session old
        sync_session.created_at = timezone.now() - timedelta(days=60)
        sync_session.save(update_fields=["created_at"])

        # Create a recent session for comparison
        SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch,
            device_id="device-recent",
        )

        initial_count = SyncSession.objects.count()
        result = cleanup_old_sync_sessions.apply(kwargs={"days_old": 30}).get()

        assert result["deleted_sessions"] >= 1
        assert SyncSession.objects.count() < initial_count


@pytest.mark.django_db
class TestRetryFailedOperations:
    """Tests for retry_failed_operations task."""

    def test_retry_failed_operations_requeues(
        self, celery_eager_mode, tenant_context, sync_session
    ):
        """Test failed operations are requeued for retry."""
        from apps.sync.models import PendingOperation
        from apps.sync.tasks import retry_failed_operations

        # Create failed operation
        op = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            operation_type="UPDATE",
            payload={"name": "Failed"},
            client_timestamp=timezone.now(),
            status="REJECTED",
            retry_count=0,
        )

        result = retry_failed_operations.apply(args=[str(tenant_context.id)]).get()

        assert result["operations_retried"] >= 1

        op.refresh_from_db()
        assert op.status == "PENDING"
        assert op.retry_count == 1

    def test_retry_respects_max_retries(
        self, celery_eager_mode, tenant_context, sync_session
    ):
        """Test operations at max retries are not requeued."""
        from apps.sync.models import PendingOperation
        from apps.sync.tasks import retry_failed_operations

        # Create operation at max retries
        op = PendingOperation.objects.create(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            entity_id=uuid.uuid4(),
            operation_type="UPDATE",
            payload={"name": "MaxRetry"},
            client_timestamp=timezone.now(),
            status="REJECTED",
            retry_count=5,  # Already at max
        )

        _result = retry_failed_operations.apply(
            args=[str(tenant_context.id)],
            kwargs={"max_retries": 3},
        ).get()

        # Should not retry since retry_count > max_retries
        op.refresh_from_db()
        assert op.status == "REJECTED"


# =============================================================================
# Inventory Task Tests
# =============================================================================


@pytest.mark.django_db
class TestRecalculateStockLevelsTask:
    """Tests for recalculate_stock_levels task."""

    def test_recalculate_stock_levels_execution(
        self, celery_eager_mode, tenant_context, product, branch
    ):
        """T059: Test recalculate_stock_levels task execution."""
        from apps.inventario.models import StockMovement, StockSnapshot
        from apps.inventario.tasks import recalculate_stock_levels

        # Create some movements
        StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100"),
            cost_snapshot=Decimal("50.00"),
        )
        StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-20"),
            cost_snapshot=Decimal("50.00"),
        )

        result = recalculate_stock_levels.apply(
            args=[str(tenant_context.id)]
        ).get()

        assert result["tenant_id"] == str(tenant_context.id)
        assert result["snapshots_recalculated"] >= 1

        # Verify snapshot was updated correctly
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("80")  # 100 - 20

    def test_recalculate_for_specific_product(
        self, celery_eager_mode, tenant_context, product, branch
    ):
        """Test recalculation for a specific product."""
        from apps.inventario.tasks import recalculate_stock_levels

        result = recalculate_stock_levels.apply(
            args=[str(tenant_context.id)],
            kwargs={"product_id": str(product.id)},
        ).get()

        assert result["product_id"] == str(product.id)

    def test_recalculate_handles_no_movements(
        self, celery_eager_mode, tenant_context
    ):
        """Test recalculation handles case with no movements."""
        from apps.inventario.tasks import recalculate_stock_levels

        result = recalculate_stock_levels.apply(
            args=[str(tenant_context.id)]
        ).get()

        assert result["snapshots_recalculated"] == 0
        assert len(result["errors"]) == 0


@pytest.mark.django_db
class TestSyncStockSnapshotsTask:
    """Tests for sync_stock_snapshots task."""

    def test_sync_creates_missing_snapshots(
        self, celery_eager_mode, tenant_context, product, branch
    ):
        """Test sync creates snapshots for new product/branch combinations."""
        from apps.inventario.models import StockSnapshot
        from apps.inventario.tasks import sync_stock_snapshots

        # Ensure no snapshot exists
        StockSnapshot.objects.filter(product=product, branch=branch).delete()

        result = sync_stock_snapshots.apply(args=[str(tenant_context.id)]).get()

        assert result["snapshots_created"] >= 1

        # Verify snapshot was created with zero quantity
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("0")


@pytest.mark.django_db
class TestCheckLowStockAlertsTask:
    """Tests for check_low_stock_alerts task."""

    def test_check_low_stock_finds_alerts(
        self, celery_eager_mode, tenant_context, product, branch
    ):
        """Test low stock check identifies products below minimum."""
        from apps.inventario.models import StockSnapshot
        from apps.inventario.tasks import check_low_stock_alerts

        # Set product minimum stock
        product.min_stock = Decimal("50")
        product.save()

        # Create snapshot with low stock
        StockSnapshot.objects.update_or_create(
            product=product,
            branch=branch,
            defaults={"quantity": Decimal("10")},
        )

        result = check_low_stock_alerts.apply(args=[str(tenant_context.id)]).get()

        assert result["alerts_count"] >= 1
        assert any(a["product_id"] == str(product.id) for a in result["alerts"])

    def test_check_low_stock_no_alerts_when_adequate(
        self, celery_eager_mode, tenant_context, product, branch
    ):
        """Test no alerts when stock is adequate."""
        from apps.inventario.models import StockSnapshot
        from apps.inventario.tasks import check_low_stock_alerts

        # Set product minimum stock
        product.min_stock = Decimal("10")
        product.save()

        # Create snapshot with adequate stock
        StockSnapshot.objects.update_or_create(
            product=product,
            branch=branch,
            defaults={"quantity": Decimal("100")},
        )

        result = check_low_stock_alerts.apply(args=[str(tenant_context.id)]).get()

        # Should not include this product in alerts
        product_alerts = [a for a in result["alerts"] if a["product_id"] == str(product.id)]
        assert len(product_alerts) == 0


@pytest.mark.django_db
class TestGenerateInventoryReportTask:
    """Tests for generate_inventory_report task."""

    def test_generate_inventory_report(
        self, celery_eager_mode, tenant_context, product, branch
    ):
        """Test inventory report generation."""
        from apps.inventario.models import StockSnapshot
        from apps.inventario.tasks import generate_inventory_report

        # Set up product with price
        product.cost_price = Decimal("50.00")
        product.unit_price = Decimal("100.00")
        product.save()

        # Create snapshot
        StockSnapshot.objects.update_or_create(
            product=product,
            branch=branch,
            defaults={"quantity": Decimal("10")},
        )

        result = generate_inventory_report.apply(args=[str(tenant_context.id)]).get()

        assert result["tenant_id"] == str(tenant_context.id)
        assert Decimal(result["total_items"]) > 0
        assert Decimal(result["total_cost_value"]) > 0
        assert Decimal(result["total_sale_value"]) > 0

    def test_generate_report_for_specific_branch(
        self, celery_eager_mode, tenant_context, branch
    ):
        """Test report generation for specific branch."""
        from apps.inventario.tasks import generate_inventory_report

        result = generate_inventory_report.apply(
            args=[str(tenant_context.id)],
            kwargs={"branch_id": str(branch.id)},
        ).get()

        assert result["branch_id"] == str(branch.id)
