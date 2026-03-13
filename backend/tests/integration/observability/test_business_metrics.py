"""
Integration tests for business metrics tenant isolation.

Tests multi-tenant metric recording and isolation.
Per 004-observability-metrics spec FR-001 through FR-010.
"""

import pytest
from django.test import Client, TestCase, override_settings
from prometheus_client import REGISTRY

from apps.core.observability.business_metrics import (
    auth_attempts_total,
    auth_failures_total,
    inventory_movements_total,
    orders_total,
    record_auth_attempt,
    record_auth_failure,
    record_inventory_movement,
    record_order,
    record_sync_operation,
    sync_operations_total,
    sync_queue_depth,
    update_sync_queue_depth,
)


class TestMultiTenantMetricIsolation(TestCase):
    """T073: Integration test for multi-tenant metric isolation."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.tenant_a = "integration-tenant-A"
        self.tenant_b = "integration-tenant-B"
        self.tenant_c = "integration-tenant-C"

    def test_orders_isolated_between_tenants(self):
        """T073: Test order metrics are isolated per tenant."""
        # Record orders for different tenants
        for _ in range(3):
            record_order(
                tenant_id=self.tenant_a,
                branch_id="branch-1",
                status="completed",
            )

        for _ in range(5):
            record_order(
                tenant_id=self.tenant_b,
                branch_id="branch-1",
                status="completed",
            )

        record_order(
            tenant_id=self.tenant_c,
            branch_id="branch-1",
            status="completed",
        )

        # Verify isolation
        tenant_a_orders = orders_total.labels(
            tenant_id=self.tenant_a,
            branch_id="branch-1",
            status="completed",
        )._value.get()

        tenant_b_orders = orders_total.labels(
            tenant_id=self.tenant_b,
            branch_id="branch-1",
            status="completed",
        )._value.get()

        tenant_c_orders = orders_total.labels(
            tenant_id=self.tenant_c,
            branch_id="branch-1",
            status="completed",
        )._value.get()

        # Each tenant should have their own count
        assert tenant_a_orders >= 3
        assert tenant_b_orders >= 5
        assert tenant_c_orders >= 1

        # Tenant B should have more than tenant A
        assert tenant_b_orders > tenant_a_orders

    def test_inventory_isolated_between_tenants(self):
        """T073: Test inventory metrics are isolated per tenant."""
        # Record inventory movements for different tenants
        record_inventory_movement(
            tenant_id=self.tenant_a,
            operation="sale",
            product_type="beverage",
            quantity=10,
        )

        record_inventory_movement(
            tenant_id=self.tenant_b,
            operation="sale",
            product_type="beverage",
            quantity=25,
        )

        # Verify isolation
        tenant_a_inv = inventory_movements_total.labels(
            tenant_id=self.tenant_a,
            branch_id="unknown",
            operation="sale",
            product_type="beverage",
        )._value.get()

        tenant_b_inv = inventory_movements_total.labels(
            tenant_id=self.tenant_b,
            branch_id="unknown",
            operation="sale",
            product_type="beverage",
        )._value.get()

        assert tenant_a_inv >= 10
        assert tenant_b_inv >= 25

    def test_sync_queue_isolated_between_tenants(self):
        """T073: Test sync queue metrics are isolated per tenant."""
        # Set different queue depths for each tenant
        update_sync_queue_depth(tenant_id=self.tenant_a, depth=100)
        update_sync_queue_depth(tenant_id=self.tenant_b, depth=50)
        update_sync_queue_depth(tenant_id=self.tenant_c, depth=200)

        # Verify isolation
        tenant_a_depth = sync_queue_depth.labels(
            tenant_id=self.tenant_a,
            operation_type="all",
        )._value.get()

        tenant_b_depth = sync_queue_depth.labels(
            tenant_id=self.tenant_b,
            operation_type="all",
        )._value.get()

        tenant_c_depth = sync_queue_depth.labels(
            tenant_id=self.tenant_c,
            operation_type="all",
        )._value.get()

        assert tenant_a_depth == 100
        assert tenant_b_depth == 50
        assert tenant_c_depth == 200

    def test_auth_metrics_isolated_between_tenants(self):
        """T073: Test auth metrics are isolated per tenant."""
        # Record auth attempts for different tenants
        for _ in range(10):
            record_auth_attempt(tenant_id=self.tenant_a, method="pwd")

        for _ in range(3):
            record_auth_attempt(tenant_id=self.tenant_b, method="pwd")

        # Record failures
        for _ in range(2):
            record_auth_failure(tenant_id=self.tenant_a, reason="invalid_creds")

        record_auth_failure(tenant_id=self.tenant_b, reason="invalid_creds")

        # Verify isolation
        tenant_a_attempts = auth_attempts_total.labels(
            tenant_id=self.tenant_a,
            method="pwd",
        )._value.get()

        tenant_b_attempts = auth_attempts_total.labels(
            tenant_id=self.tenant_b,
            method="pwd",
        )._value.get()

        tenant_a_failures = auth_failures_total.labels(
            tenant_id=self.tenant_a,
            reason="invalid_creds",
        )._value.get()

        tenant_b_failures = auth_failures_total.labels(
            tenant_id=self.tenant_b,
            reason="invalid_creds",
        )._value.get()

        assert tenant_a_attempts >= 10
        assert tenant_b_attempts >= 3
        assert tenant_a_failures >= 2
        assert tenant_b_failures >= 1

    def test_sync_operations_isolated_between_tenants(self):
        """T073: Test sync operation counters are isolated per tenant."""
        # Record sync operations for different tenants
        for _ in range(5):
            record_sync_operation(
                tenant_id=self.tenant_a,
                operation_type="create",
                status="success",
            )

        for _ in range(3):
            record_sync_operation(
                tenant_id=self.tenant_b,
                operation_type="create",
                status="success",
            )

        # Add some failures
        record_sync_operation(
            tenant_id=self.tenant_a,
            operation_type="create",
            status="failure",
        )

        # Verify isolation
        tenant_a_success = sync_operations_total.labels(
            tenant_id=self.tenant_a,
            operation_type="create",
            status="success",
        )._value.get()

        tenant_b_success = sync_operations_total.labels(
            tenant_id=self.tenant_b,
            operation_type="create",
            status="success",
        )._value.get()

        tenant_a_failure = sync_operations_total.labels(
            tenant_id=self.tenant_a,
            operation_type="create",
            status="failure",
        )._value.get()

        assert tenant_a_success >= 5
        assert tenant_b_success >= 3
        assert tenant_a_failure >= 1


class TestMetricsWithDjangoContext(TestCase):
    """Test business metrics within Django request context."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_metrics_endpoint_includes_business_metrics(self):
        """Test /metrics endpoint exposes business metrics."""
        # Record some business metrics
        record_order(
            tenant_id="django-test",
            branch_id="test-branch",
            status="completed",
        )

        # Request metrics endpoint
        response = self.client.get("/metrics")

        # Should be successful
        assert response.status_code == 200

        # Should include business metrics
        content = response.content.decode("utf-8")
        assert "orders_total" in content

    def test_metrics_survive_request_cycle(self):
        """Test metrics persist across request cycles."""
        # Record metric before request
        initial = orders_total.labels(
            tenant_id="cycle-test",
            branch_id="b1",
            status="completed",
        )._value.get()

        record_order(
            tenant_id="cycle-test",
            branch_id="b1",
            status="completed",
        )

        # Make some HTTP requests
        self.client.get("/health/live")
        self.client.get("/health/ready")

        # Record another metric after requests
        record_order(
            tenant_id="cycle-test",
            branch_id="b1",
            status="completed",
        )

        # Verify metrics persisted
        final = orders_total.labels(
            tenant_id="cycle-test",
            branch_id="b1",
            status="completed",
        )._value.get()

        assert final >= initial + 2


class TestConcurrentMetricUpdates(TestCase):
    """Test metrics handle concurrent updates correctly."""

    def test_concurrent_counter_increments(self):
        """Test counter handles concurrent increments."""
        import concurrent.futures

        tenant_id = "concurrent-test"
        num_increments = 100

        initial = orders_total.labels(
            tenant_id=tenant_id,
            branch_id="b1",
            status="completed",
        )._value.get()

        def increment():
            record_order(
                tenant_id=tenant_id,
                branch_id="b1",
                status="completed",
            )

        # Execute increments concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(increment) for _ in range(num_increments)]
            concurrent.futures.wait(futures)

        # Verify all increments were recorded
        final = orders_total.labels(
            tenant_id=tenant_id,
            branch_id="b1",
            status="completed",
        )._value.get()

        assert final >= initial + num_increments

    def test_concurrent_gauge_updates(self):
        """Test gauge handles concurrent updates."""
        import concurrent.futures

        tenant_id = "gauge-concurrent"
        final_value = 42

        def update(value):
            update_sync_queue_depth(tenant_id=tenant_id, depth=value)

        # Execute updates concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update, i) for i in range(50)]
            concurrent.futures.wait(futures)

        # Set final value
        update_sync_queue_depth(tenant_id=tenant_id, depth=final_value)

        # Verify final value is correct
        value = sync_queue_depth.labels(
            tenant_id=tenant_id,
            operation_type="all",
        )._value.get()

        assert value == final_value


class TestMetricLabelValidation(TestCase):
    """Test metric label handling and validation."""

    def test_empty_tenant_id_handled(self):
        """Test empty tenant_id doesn't cause errors."""
        # Should not raise
        record_order(tenant_id="", branch_id="b1", status="completed")
        record_inventory_movement(tenant_id="", operation="sale")
        record_auth_attempt(tenant_id="", method="pwd")
        update_sync_queue_depth(tenant_id="", depth=10)

    def test_special_characters_in_labels(self):
        """Test special characters in label values."""
        # Should handle special characters gracefully
        record_order(
            tenant_id="tenant/with/slashes",
            branch_id="branch:with:colons",
            status="completed",
        )

        record_order(
            tenant_id="tenant-with-dashes",
            branch_id="branch_with_underscores",
            status="completed",
        )

        # No exception = pass

    def test_unicode_in_labels(self):
        """Test unicode characters in label values."""
        # Should handle unicode
        record_order(
            tenant_id="tenant-café",
            branch_id="branch-日本語",
            status="completed",
        )

        # No exception = pass

    def test_very_long_label_values(self):
        """Test very long label values."""
        long_tenant = "t" * 1000
        long_branch = "b" * 1000

        # Should handle long values
        record_order(
            tenant_id=long_tenant,
            branch_id=long_branch,
            status="completed",
        )

        # No exception = pass


class TestBusinessMetricScenarios(TestCase):
    """Test realistic business metric scenarios."""

    def test_order_lifecycle_metrics(self):
        """Test metrics for a complete order lifecycle."""
        tenant = "lifecycle-test"
        branch = "store-1"

        # Order created (pending)
        record_order(tenant_id=tenant, branch_id=branch, status="pending")

        # Order completed
        record_order(tenant_id=tenant, branch_id=branch, status="completed")

        # Order had inventory impact
        record_inventory_movement(
            tenant_id=tenant,
            branch_id=branch,
            operation="sale",
            product_type="beverage",
            quantity=5,
        )

        # Verify all recorded
        pending = orders_total.labels(
            tenant_id=tenant,
            branch_id=branch,
            status="pending",
        )._value.get()

        completed = orders_total.labels(
            tenant_id=tenant,
            branch_id=branch,
            status="completed",
        )._value.get()

        inventory = inventory_movements_total.labels(
            tenant_id=tenant,
            branch_id=branch,
            operation="sale",
            product_type="beverage",
        )._value.get()

        assert pending >= 1
        assert completed >= 1
        assert inventory >= 5

    def test_auth_flow_metrics(self):
        """Test metrics for authentication flow."""
        tenant = "auth-flow-test"

        # Login attempt
        record_auth_attempt(tenant_id=tenant, method="pwd")

        # Failed attempt
        record_auth_failure(tenant_id=tenant, reason="invalid_creds")

        # Second attempt
        record_auth_attempt(tenant_id=tenant, method="pwd")

        # Verify
        attempts = auth_attempts_total.labels(
            tenant_id=tenant,
            method="pwd",
        )._value.get()

        failures = auth_failures_total.labels(
            tenant_id=tenant,
            reason="invalid_creds",
        )._value.get()

        assert attempts >= 2
        assert failures >= 1

    def test_sync_workflow_metrics(self):
        """Test metrics for sync workflow."""
        tenant = "sync-flow-test"

        # Queue has pending operations
        update_sync_queue_depth(tenant_id=tenant, depth=10)

        # Process some operations
        for _ in range(5):
            record_sync_operation(
                tenant_id=tenant,
                operation_type="create",
                status="success",
            )

        # Update queue depth
        update_sync_queue_depth(tenant_id=tenant, depth=5)

        # One conflict
        record_sync_operation(
            tenant_id=tenant,
            operation_type="update",
            status="conflict",
        )

        # Verify
        depth = sync_queue_depth.labels(
            tenant_id=tenant,
            operation_type="all",
        )._value.get()

        success_count = sync_operations_total.labels(
            tenant_id=tenant,
            operation_type="create",
            status="success",
        )._value.get()

        conflict_count = sync_operations_total.labels(
            tenant_id=tenant,
            operation_type="update",
            status="conflict",
        )._value.get()

        assert depth == 5
        assert success_count >= 5
        assert conflict_count >= 1
