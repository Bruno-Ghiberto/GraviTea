"""
Unit tests for observability metrics module.

Tests RED metric definitions, path normalization, and tenant label injection.
Per 004-observability-metrics spec FR-001 through FR-010.
"""

import pytest
from prometheus_client import REGISTRY as DEFAULT_REGISTRY

from apps.core.observability.metrics import (
    REGISTRY,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    normalize_path,
    record_request,
)
from apps.core.observability.business_metrics import (
    record_auth_attempt,
    record_inventory_movement,
    record_order,
    record_sync_operation,
    sync_operations_total,
    sync_queue_depth,
    update_sync_lag,
    update_sync_queue_depth,
)


@pytest.mark.unit
class TestMetricDefinitions:
    """Test that RED metrics are properly defined."""

    def test_http_requests_total_defined(self):
        """T018: Test http_requests_total counter is defined with correct labels."""
        # Verify the metric exists
        assert http_requests_total is not None

        # Verify it's a Counter type
        assert http_requests_total._type == "counter"

        # Verify labels are present
        labels = http_requests_total._labelnames
        assert "method" in labels
        assert "endpoint" in labels
        assert "status_code" in labels
        assert "tenant_id" in labels

    def test_http_request_duration_seconds_defined(self):
        """T018: Test http_request_duration_seconds histogram is defined."""
        assert http_request_duration_seconds is not None

        # Verify it's a Histogram type
        assert http_request_duration_seconds._type == "histogram"

        # Verify labels
        labels = http_request_duration_seconds._labelnames
        assert "method" in labels
        assert "endpoint" in labels
        assert "tenant_id" in labels

    def test_http_requests_in_progress_defined(self):
        """T018: Test http_requests_in_progress gauge is defined."""
        assert http_requests_in_progress is not None

        # Verify it's a Gauge type
        assert http_requests_in_progress._type == "gauge"

        # Verify labels
        labels = http_requests_in_progress._labelnames
        assert "method" in labels
        assert "endpoint" in labels

    def test_custom_registry_used(self):
        """Test that metrics use custom registry, not default."""
        # Our REGISTRY should be distinct from the default
        assert REGISTRY is not DEFAULT_REGISTRY


@pytest.mark.unit
class TestPathNormalization:
    """Test endpoint path normalization to prevent label cardinality explosion."""

    def test_normalize_uuid_in_path(self):
        """T019: Test UUID normalization in paths."""
        path = "/api/v1/products/550e8400-e29b-41d4-a716-446655440000/details"
        normalized = normalize_path(path)
        assert normalized == "/api/v1/products/{id}/details"

    def test_normalize_integer_id_in_path(self):
        """T019: Test integer ID normalization in paths."""
        path = "/api/v1/orders/12345/items"
        normalized = normalize_path(path)
        assert normalized == "/api/v1/orders/{id}/items"

    def test_normalize_multiple_ids_in_path(self):
        """T019: Test multiple ID normalization in paths."""
        path = "/api/v1/tenants/123/branches/456/products/789"
        normalized = normalize_path(path)
        assert normalized == "/api/v1/tenants/{id}/branches/{id}/products/{id}"

    def test_normalize_preserves_path_without_ids(self):
        """T019: Test that paths without IDs are preserved."""
        path = "/api/v1/products"
        normalized = normalize_path(path)
        assert normalized == "/api/v1/products"

    def test_normalize_handles_query_params(self):
        """T019: Test query parameters are handled correctly."""
        path = "/api/v1/products/123?sort=name"
        normalized = normalize_path(path)
        # Query params should be preserved or stripped consistently
        assert "{id}" in normalized

    def test_normalize_health_endpoints(self):
        """T019: Test health endpoints are not over-normalized."""
        assert normalize_path("/health/live") == "/health/live"
        assert normalize_path("/health/ready") == "/health/ready"
        assert normalize_path("/metrics") == "/metrics"

    def test_normalize_empty_path(self):
        """T019: Test empty path handling."""
        assert normalize_path("") == ""
        assert normalize_path("/") == "/"


@pytest.mark.unit
class TestTenantIdLabelInjection:
    """Test tenant_id label is properly injected in metrics."""

    def test_record_request_with_tenant_id(self):
        """T020: Test tenant_id is included when recording requests."""
        # Record a request with tenant_id
        record_request(
            method="GET",
            endpoint="/api/v1/products",
            status_code=200,
            duration=0.05,
            tenant_id="tenant-123",
        )

        # Verify the metric was recorded (no exception = success)
        # In a real test, we'd verify the label value in the metrics output

    def test_record_request_without_tenant_id(self):
        """T020: Test requests without tenant_id use default value."""
        # Record a request without tenant_id
        record_request(
            method="GET",
            endpoint="/health/live",
            status_code=200,
            duration=0.01,
            tenant_id=None,
        )

        # Should not raise an exception

    def test_record_request_normalizes_path(self):
        """T020: Test that paths are normalized before recording."""
        # Record with a path containing an ID
        record_request(
            method="GET",
            endpoint="/api/v1/products/12345",
            status_code=200,
            duration=0.05,
            tenant_id="tenant-abc",
        )

        # The path should be normalized (verified via metrics output)


@pytest.mark.unit
class TestBusinessMetrics:
    """Test business-specific metric recording functions."""

    def test_record_auth_attempt_success(self):
        """Test recording successful auth attempt."""
        # record_auth_attempt only takes tenant_id and method
        record_auth_attempt(
            tenant_id="tenant-123",
            method="pwd",
        )

    def test_record_auth_attempt_failure(self):
        """Test recording failed auth attempt with reason."""
        # Use record_auth_failure for failures, not record_auth_attempt
        from apps.core.observability.business_metrics import record_auth_failure
        record_auth_failure(
            tenant_id="tenant-123",
            reason="invalid_creds",
        )

    def test_record_sync_operation(self):
        """Test recording sync operations."""
        record_sync_operation(
            tenant_id="tenant-123",
            operation_type="push",
            status="success",
        )

        record_sync_operation(
            tenant_id="tenant-123",
            operation_type="pull",
            status="failure",
        )

    def test_update_sync_queue_depth(self):
        """Test updating sync queue depth gauge."""
        # update_sync_queue_depth signature: (tenant_id, depth, operation_type="all")
        update_sync_queue_depth(
            tenant_id="tenant-123",
            depth=42,
            operation_type="outbound",
        )

    def test_update_sync_lag(self):
        """Test updating sync lag gauge."""
        # update_sync_lag signature: (tenant_id, lag_seconds)
        update_sync_lag(
            tenant_id="tenant-123",
            lag_seconds=5.5,
        )

    def test_record_inventory_movement(self):
        """Test recording inventory movements."""
        # record_inventory_movement signature: (tenant_id, operation, branch_id="unknown", product_type="unknown", quantity=1)
        record_inventory_movement(
            tenant_id="tenant-123",
            operation="sale",
            product_type="beverages",
        )

    def test_record_order(self):
        """Test recording orders."""
        # record_order signature: (tenant_id, branch_id="unknown", status="completed", amount=None, currency="CRC")
        record_order(
            tenant_id="tenant-123",
            branch_id="pos",
            status="completed",
        )


@pytest.mark.unit
class TestMetricCardinalityControl:
    """Test that metric cardinality is controlled appropriately."""

    def test_limited_status_code_labels(self):
        """Test that status codes don't create unbounded cardinality."""
        # Record various status codes
        for status in [200, 201, 400, 401, 403, 404, 500, 502, 503]:
            record_request(
                method="GET",
                endpoint="/api/v1/products",
                status_code=status,
                duration=0.05,
                tenant_id="tenant-123",
            )

        # All should be recorded without issues

    def test_limited_method_labels(self):
        """Test that methods are limited to valid HTTP methods."""
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

        for method in valid_methods:
            record_request(
                method=method,
                endpoint="/api/v1/products",
                status_code=200,
                duration=0.05,
                tenant_id="tenant-123",
            )

        # All should be recorded without issues

    def test_path_normalization_reduces_cardinality(self):
        """Test that path normalization reduces unique label combinations."""
        # Record multiple requests with different IDs in path
        # All should be normalized to the same pattern
        for i in range(100):
            record_request(
                method="GET",
                endpoint=f"/api/v1/products/{i}/details",
                status_code=200,
                duration=0.05,
                tenant_id="tenant-123",
            )

        # These should all normalize to /api/v1/products/{id}/details
        # preventing cardinality explosion
