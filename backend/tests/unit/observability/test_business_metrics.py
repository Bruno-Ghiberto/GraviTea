"""
Unit tests for business metrics.

Tests orders, inventory, sync queue, and auth metrics.
Per 004-observability-metrics spec FR-001 through FR-010.
"""

import pytest
from prometheus_client import REGISTRY
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from apps.core.observability.business_metrics import (
    active_sessions,
    auth_attempts_total,
    auth_failures_total,
    auth_success_total,
    inventory_movements_total,
    low_stock_alerts,
    orders_in_progress,
    orders_total,
    record_auth_attempt,
    record_auth_failure,
    record_auth_success,
    record_inventory_movement,
    record_order,
    record_sync_operation,
    sync_operations_total,
    sync_processing_lag_seconds,
    sync_queue_depth,
    update_active_sessions,
    update_low_stock_count,
    update_sync_lag,
    update_sync_queue_depth,
)
from apps.core.observability.metrics import REGISTRY as OBS_REGISTRY


@pytest.mark.unit
class TestOrdersMetric:
    """T069: Unit test for orders_total metric."""

    def test_orders_total_exists(self):
        """T069: Test orders_total counter is defined."""
        assert orders_total is not None
        # Prometheus Counter internal name doesn't include _total suffix
        # (the suffix is added during export)
        assert orders_total._name == "orders"

    def test_orders_total_has_correct_labels(self):
        """T069: Test orders_total has required labels."""
        expected_labels = {"tenant_id", "branch_id", "status"}
        assert set(orders_total._labelnames) == expected_labels

    def test_record_order_increments_counter(self):
        """T069: Test record_order increments the counter."""
        # Get current value
        initial = orders_total.labels(
            tenant_id="test-tenant",
            branch_id="test-branch",
            status="completed",
        )._value.get()

        # Record an order
        record_order(
            tenant_id="test-tenant",
            branch_id="test-branch",
            status="completed",
        )

        # Verify increment
        new_value = orders_total.labels(
            tenant_id="test-tenant",
            branch_id="test-branch",
            status="completed",
        )._value.get()

        assert new_value == initial + 1

    def test_record_order_with_different_statuses(self):
        """T069: Test orders are tracked by status."""
        for status in ["completed", "cancelled", "pending"]:
            record_order(
                tenant_id="status-test",
                branch_id="branch-1",
                status=status,
            )

        # All should be recorded separately
        completed = orders_total.labels(
            tenant_id="status-test",
            branch_id="branch-1",
            status="completed",
        )._value.get()

        cancelled = orders_total.labels(
            tenant_id="status-test",
            branch_id="branch-1",
            status="cancelled",
        )._value.get()

        assert completed >= 1
        assert cancelled >= 1

    def test_record_order_tenant_isolation(self):
        """T069: Test orders are isolated per tenant."""
        record_order(tenant_id="tenant-A", branch_id="b1", status="completed")
        record_order(tenant_id="tenant-B", branch_id="b1", status="completed")

        # Should track separately
        tenant_a = orders_total.labels(
            tenant_id="tenant-A",
            branch_id="b1",
            status="completed",
        )._value.get()

        tenant_b = orders_total.labels(
            tenant_id="tenant-B",
            branch_id="b1",
            status="completed",
        )._value.get()

        # Both should have at least one
        assert tenant_a >= 1
        assert tenant_b >= 1


@pytest.mark.unit
class TestInventoryMovementsMetric:
    """T070: Unit test for inventory_movements_total metric."""

    def test_inventory_movements_exists(self):
        """T070: Test inventory_movements_total counter is defined."""
        assert inventory_movements_total is not None
        # Prometheus Counter internal name doesn't include _total suffix
        assert inventory_movements_total._name == "inventory_movements"

    def test_inventory_movements_has_correct_labels(self):
        """T070: Test inventory_movements_total has required labels."""
        expected_labels = {"tenant_id", "branch_id", "operation", "product_type"}
        assert set(inventory_movements_total._labelnames) == expected_labels

    def test_record_inventory_movement_increments_counter(self):
        """T070: Test record_inventory_movement increments counter."""
        initial = inventory_movements_total.labels(
            tenant_id="inv-test",
            branch_id="branch-1",
            operation="sale",
            product_type="beverage",
        )._value.get()

        record_inventory_movement(
            tenant_id="inv-test",
            branch_id="branch-1",
            operation="sale",
            product_type="beverage",
        )

        new_value = inventory_movements_total.labels(
            tenant_id="inv-test",
            branch_id="branch-1",
            operation="sale",
            product_type="beverage",
        )._value.get()

        assert new_value == initial + 1

    def test_record_inventory_movement_with_quantity(self):
        """T070: Test inventory movement with quantity > 1."""
        initial = inventory_movements_total.labels(
            tenant_id="qty-test",
            branch_id="b1",
            operation="purchase",
            product_type="food",
        )._value.get()

        record_inventory_movement(
            tenant_id="qty-test",
            branch_id="b1",
            operation="purchase",
            product_type="food",
            quantity=5,
        )

        new_value = inventory_movements_total.labels(
            tenant_id="qty-test",
            branch_id="b1",
            operation="purchase",
            product_type="food",
        )._value.get()

        assert new_value == initial + 5

    def test_inventory_movement_operations(self):
        """T070: Test different inventory operations."""
        operations = ["sale", "purchase", "transfer", "adjustment"]

        for op in operations:
            record_inventory_movement(
                tenant_id="op-test",
                operation=op,
                product_type="generic",
            )

        # Each operation should be tracked
        for op in operations:
            val = inventory_movements_total.labels(
                tenant_id="op-test",
                branch_id="unknown",
                operation=op,
                product_type="generic",
            )._value.get()
            assert val >= 1


@pytest.mark.unit
class TestSyncQueueDepthMetric:
    """T071: Unit test for sync_queue_depth metric."""

    def test_sync_queue_depth_exists(self):
        """T071: Test sync_queue_depth gauge is defined."""
        assert sync_queue_depth is not None
        assert sync_queue_depth._name == "sync_queue_depth"

    def test_sync_queue_depth_has_correct_labels(self):
        """T071: Test sync_queue_depth has required labels."""
        expected_labels = {"tenant_id", "operation_type"}
        assert set(sync_queue_depth._labelnames) == expected_labels

    def test_update_sync_queue_depth(self):
        """T071: Test update_sync_queue_depth sets gauge value."""
        update_sync_queue_depth(tenant_id="sync-test", depth=42)

        value = sync_queue_depth.labels(
            tenant_id="sync-test",
            operation_type="all",
        )._value.get()

        assert value == 42

    def test_update_sync_queue_depth_by_operation(self):
        """T071: Test sync queue depth by operation type."""
        update_sync_queue_depth(tenant_id="op-sync", depth=10, operation_type="create")
        update_sync_queue_depth(tenant_id="op-sync", depth=5, operation_type="update")

        create_val = sync_queue_depth.labels(
            tenant_id="op-sync",
            operation_type="create",
        )._value.get()

        update_val = sync_queue_depth.labels(
            tenant_id="op-sync",
            operation_type="update",
        )._value.get()

        assert create_val == 10
        assert update_val == 5

    def test_sync_processing_lag_exists(self):
        """T071: Test sync_processing_lag_seconds gauge is defined."""
        assert sync_processing_lag_seconds is not None
        assert sync_processing_lag_seconds._name == "sync_processing_lag_seconds"

    def test_update_sync_lag(self):
        """T071: Test update_sync_lag sets gauge value."""
        update_sync_lag(tenant_id="lag-test", lag_seconds=30.5)

        value = sync_processing_lag_seconds.labels(
            tenant_id="lag-test",
        )._value.get()

        assert value == 30.5

    def test_sync_operations_counter(self):
        """T071: Test sync_operations_total counter."""
        initial = sync_operations_total.labels(
            tenant_id="sync-op-test",
            operation_type="create",
            status="success",
        )._value.get()

        record_sync_operation(
            tenant_id="sync-op-test",
            operation_type="create",
            status="success",
        )

        new_value = sync_operations_total.labels(
            tenant_id="sync-op-test",
            operation_type="create",
            status="success",
        )._value.get()

        assert new_value == initial + 1


@pytest.mark.unit
class TestAuthAttemptsMetric:
    """T072: Unit test for auth_attempts_total metric."""

    def test_auth_attempts_exists(self):
        """T072: Test auth_attempts_total counter is defined."""
        assert auth_attempts_total is not None
        # Prometheus Counter internal name doesn't include _total suffix
        assert auth_attempts_total._name == "auth_attempts"

    def test_auth_attempts_has_correct_labels(self):
        """T072: Test auth_attempts_total has required labels."""
        expected_labels = {"tenant_id", "method"}
        assert set(auth_attempts_total._labelnames) == expected_labels

    def test_record_auth_attempt_increments_counter(self):
        """T072: Test record_auth_attempt increments counter."""
        initial = auth_attempts_total.labels(
            tenant_id="auth-test",
            method="pwd",
        )._value.get()

        record_auth_attempt(
            tenant_id="auth-test",
            method="pwd",
        )

        new_value = auth_attempts_total.labels(
            tenant_id="auth-test",
            method="pwd",
        )._value.get()

        assert new_value == initial + 1

    def test_auth_failures_exists(self):
        """T072: Test auth_failures_total counter is defined."""
        assert auth_failures_total is not None
        # Prometheus Counter internal name doesn't include _total suffix
        assert auth_failures_total._name == "auth_failures"

    def test_auth_failures_has_correct_labels(self):
        """T072: Test auth_failures_total has required labels."""
        expected_labels = {"tenant_id", "reason"}
        assert set(auth_failures_total._labelnames) == expected_labels

    def test_record_auth_failure_increments_counter(self):
        """T072: Test record_auth_failure increments counter."""
        initial = auth_failures_total.labels(
            tenant_id="fail-test",
            reason="invalid_creds",
        )._value.get()

        record_auth_failure(
            tenant_id="fail-test",
            reason="invalid_creds",
        )

        new_value = auth_failures_total.labels(
            tenant_id="fail-test",
            reason="invalid_creds",
        )._value.get()

        assert new_value == initial + 1

    def test_auth_failure_reasons(self):
        """T072: Test different failure reasons are tracked."""
        reasons = ["invalid_creds", "expired_jwt", "locked_account"]

        for reason in reasons:
            record_auth_failure(tenant_id="reason-test", reason=reason)

        for reason in reasons:
            val = auth_failures_total.labels(
                tenant_id="reason-test",
                reason=reason,
            )._value.get()
            assert val >= 1

    def test_auth_methods(self):
        """T072: Test different auth methods are tracked."""
        methods = ["pwd", "jwt", "key"]

        for method in methods:
            record_auth_attempt(tenant_id="method-test", method=method)

        for method in methods:
            val = auth_attempts_total.labels(
                tenant_id="method-test",
                method=method,
            )._value.get()
            assert val >= 1

    def test_auth_success_counter(self):
        """T072: Test auth_success_total counter."""
        initial = auth_success_total.labels(
            tenant_id="success-test",
            method="pwd",
        )._value.get()

        record_auth_success(tenant_id="success-test", method="pwd")

        new_value = auth_success_total.labels(
            tenant_id="success-test",
            method="pwd",
        )._value.get()

        assert new_value == initial + 1


@pytest.mark.unit
class TestTenantIsolation:
    """Test tenant isolation for all business metrics."""

    def test_orders_tenant_isolation(self):
        """Test orders are isolated between tenants."""
        record_order(tenant_id="iso-tenant-1", branch_id="b1", status="completed")
        record_order(tenant_id="iso-tenant-2", branch_id="b1", status="completed")
        record_order(tenant_id="iso-tenant-2", branch_id="b1", status="completed")

        tenant_1_val = orders_total.labels(
            tenant_id="iso-tenant-1",
            branch_id="b1",
            status="completed",
        )._value.get()

        tenant_2_val = orders_total.labels(
            tenant_id="iso-tenant-2",
            branch_id="b1",
            status="completed",
        )._value.get()

        # Tenant 2 should have more orders
        assert tenant_2_val >= tenant_1_val

    def test_sync_metrics_tenant_isolation(self):
        """Test sync metrics are isolated between tenants."""
        update_sync_queue_depth(tenant_id="iso-sync-1", depth=10)
        update_sync_queue_depth(tenant_id="iso-sync-2", depth=20)

        val_1 = sync_queue_depth.labels(
            tenant_id="iso-sync-1",
            operation_type="all",
        )._value.get()

        val_2 = sync_queue_depth.labels(
            tenant_id="iso-sync-2",
            operation_type="all",
        )._value.get()

        assert val_1 == 10
        assert val_2 == 20

    def test_auth_metrics_tenant_isolation(self):
        """Test auth metrics are isolated between tenants."""
        record_auth_failure(tenant_id="iso-auth-1", reason="invalid_creds")
        record_auth_failure(tenant_id="iso-auth-2", reason="invalid_creds")
        record_auth_failure(tenant_id="iso-auth-2", reason="invalid_creds")

        val_1 = auth_failures_total.labels(
            tenant_id="iso-auth-1",
            reason="invalid_creds",
        )._value.get()

        val_2 = auth_failures_total.labels(
            tenant_id="iso-auth-2",
            reason="invalid_creds",
        )._value.get()

        assert val_2 >= val_1


@pytest.mark.unit
class TestMetricErrorHandling:
    """Test metrics handle errors gracefully."""

    def test_record_order_handles_exception(self):
        """Test record_order doesn't raise on error."""
        # Should not raise even with unusual inputs
        record_order(tenant_id="", branch_id="", status="")
        # No exception = pass

    def test_record_inventory_handles_exception(self):
        """Test record_inventory_movement doesn't raise on error."""
        record_inventory_movement(tenant_id="", operation="", quantity=0)
        # No exception = pass

    def test_update_sync_metrics_handles_exception(self):
        """Test sync metric updates don't raise on error."""
        update_sync_queue_depth(tenant_id="", depth=-1)
        update_sync_lag(tenant_id="", lag_seconds=-1.0)
        # No exception = pass

    def test_auth_metrics_handle_exception(self):
        """Test auth metrics don't raise on error."""
        record_auth_attempt(tenant_id="", method="")
        record_auth_failure(tenant_id="", reason="")
        # No exception = pass


@pytest.mark.unit
class TestOrdersInProgressGauge:
    """T073: Unit tests for orders_in_progress gauge metric."""

    def test_orders_in_progress_exists(self):
        """T073: Test orders_in_progress gauge is defined."""
        assert orders_in_progress is not None
        assert orders_in_progress._name == "orders_in_progress"

    def test_orders_in_progress_has_correct_labels(self):
        """T073: Test orders_in_progress has required labels."""
        expected_labels = {"tenant_id", "branch_id"}
        assert set(orders_in_progress._labelnames) == expected_labels

    def test_orders_in_progress_increment(self):
        """T073: Test orders_in_progress can be incremented."""
        initial = orders_in_progress.labels(
            tenant_id="gauge-test-tenant",
            branch_id="gauge-test-branch",
        )._value.get()

        orders_in_progress.labels(
            tenant_id="gauge-test-tenant",
            branch_id="gauge-test-branch",
        ).inc()

        new_value = orders_in_progress.labels(
            tenant_id="gauge-test-tenant",
            branch_id="gauge-test-branch",
        )._value.get()

        assert new_value == initial + 1

    def test_orders_in_progress_decrement(self):
        """T073: Test orders_in_progress can be decremented."""
        # Set to a known value first
        orders_in_progress.labels(
            tenant_id="gauge-dec-test",
            branch_id="b1",
        ).set(10)

        orders_in_progress.labels(
            tenant_id="gauge-dec-test",
            branch_id="b1",
        ).dec()

        value = orders_in_progress.labels(
            tenant_id="gauge-dec-test",
            branch_id="b1",
        )._value.get()

        assert value == 9

    def test_orders_in_progress_set_value(self):
        """T073: Test orders_in_progress can be set to specific value."""
        orders_in_progress.labels(
            tenant_id="gauge-set-test",
            branch_id="b1",
        ).set(42)

        value = orders_in_progress.labels(
            tenant_id="gauge-set-test",
            branch_id="b1",
        )._value.get()

        assert value == 42

    def test_orders_in_progress_tenant_isolation(self):
        """T073: Test orders_in_progress is isolated per tenant."""
        orders_in_progress.labels(tenant_id="gauge-iso-1", branch_id="b1").set(5)
        orders_in_progress.labels(tenant_id="gauge-iso-2", branch_id="b1").set(15)

        val_1 = orders_in_progress.labels(
            tenant_id="gauge-iso-1",
            branch_id="b1",
        )._value.get()

        val_2 = orders_in_progress.labels(
            tenant_id="gauge-iso-2",
            branch_id="b1",
        )._value.get()

        assert val_1 == 5
        assert val_2 == 15


@pytest.mark.unit
class TestLowStockAlertsGauge:
    """T073: Unit tests for low_stock_alerts gauge metric."""

    def test_low_stock_alerts_exists(self):
        """T073: Test low_stock_alerts gauge is defined."""
        assert low_stock_alerts is not None
        assert low_stock_alerts._name == "low_stock_alerts"

    def test_low_stock_alerts_has_correct_labels(self):
        """T073: Test low_stock_alerts has required labels."""
        expected_labels = {"tenant_id", "branch_id"}
        assert set(low_stock_alerts._labelnames) == expected_labels

    def test_update_low_stock_count_sets_value(self):
        """T073: Test update_low_stock_count helper sets gauge value."""
        update_low_stock_count(
            tenant_id="low-stock-test",
            branch_id="b1",
            count=25,
        )

        value = low_stock_alerts.labels(
            tenant_id="low-stock-test",
            branch_id="b1",
        )._value.get()

        assert value == 25

    def test_low_stock_alerts_increment_decrement(self):
        """T073: Test low_stock_alerts can increase and decrease."""
        low_stock_alerts.labels(
            tenant_id="low-stock-inc",
            branch_id="b1",
        ).set(0)

        # Stock falls below minimum - increment
        low_stock_alerts.labels(
            tenant_id="low-stock-inc",
            branch_id="b1",
        ).inc()

        assert low_stock_alerts.labels(
            tenant_id="low-stock-inc",
            branch_id="b1",
        )._value.get() == 1

        # Stock rises above minimum - decrement
        low_stock_alerts.labels(
            tenant_id="low-stock-inc",
            branch_id="b1",
        ).dec()

        assert low_stock_alerts.labels(
            tenant_id="low-stock-inc",
            branch_id="b1",
        )._value.get() == 0

    def test_low_stock_alerts_branch_isolation(self):
        """T073: Test low_stock_alerts is isolated per branch."""
        update_low_stock_count(tenant_id="low-stock-iso", branch_id="branch-a", count=3)
        update_low_stock_count(tenant_id="low-stock-iso", branch_id="branch-b", count=7)

        val_a = low_stock_alerts.labels(
            tenant_id="low-stock-iso",
            branch_id="branch-a",
        )._value.get()

        val_b = low_stock_alerts.labels(
            tenant_id="low-stock-iso",
            branch_id="branch-b",
        )._value.get()

        assert val_a == 3
        assert val_b == 7

    def test_update_low_stock_handles_error(self):
        """T073: Test update_low_stock_count doesn't raise on error."""
        # Should not raise even with unusual inputs
        update_low_stock_count(tenant_id="", branch_id="", count=-1)
        # No exception = pass


@pytest.mark.unit
class TestActiveSessionsGauge:
    """T073: Unit tests for active_sessions gauge metric."""

    def test_active_sessions_exists(self):
        """T073: Test active_sessions gauge is defined."""
        assert active_sessions is not None
        assert active_sessions._name == "active_sessions"

    def test_active_sessions_has_correct_labels(self):
        """T073: Test active_sessions has required labels."""
        expected_labels = {"tenant_id"}
        assert set(active_sessions._labelnames) == expected_labels

    def test_update_active_sessions_sets_value(self):
        """T073: Test update_active_sessions helper sets gauge value."""
        update_active_sessions(tenant_id="sessions-test", count=100)

        value = active_sessions.labels(
            tenant_id="sessions-test",
        )._value.get()

        assert value == 100

    def test_active_sessions_login_increment(self):
        """T073: Test active_sessions increments on login."""
        active_sessions.labels(tenant_id="login-test").set(5)

        # User logs in
        active_sessions.labels(tenant_id="login-test").inc()

        value = active_sessions.labels(tenant_id="login-test")._value.get()
        assert value == 6

    def test_active_sessions_logout_decrement(self):
        """T073: Test active_sessions decrements on logout."""
        active_sessions.labels(tenant_id="logout-test").set(10)

        # User logs out
        active_sessions.labels(tenant_id="logout-test").dec()

        value = active_sessions.labels(tenant_id="logout-test")._value.get()
        assert value == 9

    def test_active_sessions_session_expiry(self):
        """T073: Test active_sessions handles session expiry."""
        # Simulate 5 active sessions
        update_active_sessions(tenant_id="expiry-test", count=5)

        # 2 sessions expire
        active_sessions.labels(tenant_id="expiry-test").set(3)

        value = active_sessions.labels(tenant_id="expiry-test")._value.get()
        assert value == 3

    def test_active_sessions_tenant_isolation(self):
        """T073: Test active_sessions is isolated per tenant."""
        update_active_sessions(tenant_id="session-iso-1", count=20)
        update_active_sessions(tenant_id="session-iso-2", count=50)

        val_1 = active_sessions.labels(tenant_id="session-iso-1")._value.get()
        val_2 = active_sessions.labels(tenant_id="session-iso-2")._value.get()

        assert val_1 == 20
        assert val_2 == 50

    def test_update_active_sessions_handles_error(self):
        """T073: Test update_active_sessions doesn't raise on error."""
        # Should not raise even with unusual inputs
        update_active_sessions(tenant_id="", count=-1)
        # No exception = pass


@pytest.mark.unit
class TestGaugeMetricsIntegration:
    """T073: Integration tests for gauge metrics behavior."""

    def test_all_gauges_can_go_to_zero(self):
        """T073: Test all gauge metrics can be set to zero."""
        # Set all gauges to non-zero values
        orders_in_progress.labels(tenant_id="zero-test", branch_id="b1").set(10)
        low_stock_alerts.labels(tenant_id="zero-test", branch_id="b1").set(5)
        active_sessions.labels(tenant_id="zero-test").set(20)

        # Reset to zero
        orders_in_progress.labels(tenant_id="zero-test", branch_id="b1").set(0)
        low_stock_alerts.labels(tenant_id="zero-test", branch_id="b1").set(0)
        active_sessions.labels(tenant_id="zero-test").set(0)

        # Verify all are zero
        assert orders_in_progress.labels(
            tenant_id="zero-test", branch_id="b1"
        )._value.get() == 0
        assert low_stock_alerts.labels(
            tenant_id="zero-test", branch_id="b1"
        )._value.get() == 0
        assert active_sessions.labels(
            tenant_id="zero-test"
        )._value.get() == 0

    def test_gauges_handle_concurrent_updates(self):
        """T073: Test gauge metrics handle rapid updates correctly."""
        tenant = "concurrent-test"
        branch = "b1"

        # Rapid sequential updates
        for i in range(100):
            orders_in_progress.labels(
                tenant_id=tenant,
                branch_id=branch,
            ).set(i)

        # Final value should be 99
        value = orders_in_progress.labels(
            tenant_id=tenant,
            branch_id=branch,
        )._value.get()

        assert value == 99

    def test_gauge_negative_values(self):
        """T073: Test gauges can technically hold negative values."""
        # This tests Prometheus behavior - gauges can go negative
        orders_in_progress.labels(
            tenant_id="negative-test",
            branch_id="b1",
        ).set(0)

        orders_in_progress.labels(
            tenant_id="negative-test",
            branch_id="b1",
        ).dec()

        value = orders_in_progress.labels(
            tenant_id="negative-test",
            branch_id="b1",
        )._value.get()

        # Note: Gauges can go negative in Prometheus
        # Business logic should prevent this in practice
        assert value == -1
