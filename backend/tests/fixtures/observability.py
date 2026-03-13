"""
Observability test fixtures for gauge metrics.

FR-010: Test gauge metrics for orders_in_progress, low_stock_alerts, active_sessions.

This module provides isolated Prometheus registry fixtures for testing
gauge metrics without polluting the global registry.
"""

import pytest
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram
from typing import Generator

from tests.constants import (
    METRIC_ORDERS_IN_PROGRESS,
    METRIC_LOW_STOCK_ALERTS,
    METRIC_ACTIVE_SESSIONS,
    DEFAULT_TENANT_LABEL,
    DEFAULT_PRODUCT_LABEL,
)


@pytest.fixture
def isolated_registry() -> Generator[CollectorRegistry, None, None]:
    """
    Create isolated Prometheus registry for test isolation.

    FR-010: Gauge metrics must be isolated between tests.

    SCOPE: function (fresh registry per test)

    USAGE:
        def test_metric_increment(isolated_registry):
            gauge = Gauge("my_metric", "desc", registry=isolated_registry)
            gauge.inc()
            assert gauge._value.get() == 1
    """
    registry = CollectorRegistry()
    yield registry
    # Registry is automatically garbage collected after test


@pytest.fixture
def orders_gauge(isolated_registry: CollectorRegistry) -> Gauge:
    """
    Isolated orders_in_progress gauge for testing.

    METRIC: gravitea_orders_in_progress
    LABELS: tenant_id
    BEHAVIOR:
        - +1 on order created
        - -1 on order completed/cancelled/failed

    SCOPE: function (tied to isolated_registry)

    USAGE:
        def test_order_created(orders_gauge, test_tenant):
            orders_gauge.labels(tenant_id=str(test_tenant.id)).inc()
            assert orders_gauge.labels(tenant_id=str(test_tenant.id))._value.get() == 1
    """
    return Gauge(
        name=METRIC_ORDERS_IN_PROGRESS,
        documentation="Number of orders currently being processed",
        labelnames=["tenant_id"],
        registry=isolated_registry,
    )


@pytest.fixture
def stock_gauge(isolated_registry: CollectorRegistry) -> Gauge:
    """
    Isolated low_stock_alerts gauge for testing.

    METRIC: gravitea_low_stock_alerts
    LABELS: tenant_id, product_id
    BEHAVIOR:
        - +1 when stock falls below minimum
        - -1 when stock rises above minimum
        - -1 when product deleted (if was low)

    SCOPE: function (tied to isolated_registry)

    USAGE:
        def test_low_stock_alert(stock_gauge, test_tenant, test_product):
            labels = {"tenant_id": str(test_tenant.id), "product_id": str(test_product.id)}
            stock_gauge.labels(**labels).inc()
            assert stock_gauge.labels(**labels)._value.get() == 1
    """
    return Gauge(
        name=METRIC_LOW_STOCK_ALERTS,
        documentation="Number of products below minimum stock level",
        labelnames=["tenant_id", "product_id"],
        registry=isolated_registry,
    )


@pytest.fixture
def sessions_gauge(isolated_registry: CollectorRegistry) -> Gauge:
    """
    Isolated active_sessions gauge for testing.

    METRIC: gravitea_active_sessions
    LABELS: tenant_id
    BEHAVIOR:
        - +1 on user login
        - -1 on user logout
        - -1 on session expired
        - -1 on session revoked

    SCOPE: function (tied to isolated_registry)

    USAGE:
        def test_login_increments(sessions_gauge, test_tenant):
            sessions_gauge.labels(tenant_id=str(test_tenant.id)).inc()
            assert sessions_gauge.labels(tenant_id=str(test_tenant.id))._value.get() == 1
    """
    return Gauge(
        name=METRIC_ACTIVE_SESSIONS,
        documentation="Number of active user sessions",
        labelnames=["tenant_id"],
        registry=isolated_registry,
    )


@pytest.fixture
def sync_operations_gauge(isolated_registry: CollectorRegistry) -> Gauge:
    """
    Isolated sync operations gauge for testing.

    METRIC: gravitea_sync_operations_pending
    LABELS: tenant_id, device_id
    """
    return Gauge(
        name="gravitea_sync_operations_pending",
        documentation="Number of pending sync operations",
        labelnames=["tenant_id", "device_id"],
        registry=isolated_registry,
    )


@pytest.fixture
def request_counter(isolated_registry: CollectorRegistry) -> Counter:
    """
    Isolated request counter for testing.

    METRIC: gravitea_requests_total
    LABELS: tenant_id, endpoint, method, status
    """
    return Counter(
        name="gravitea_requests_total",
        documentation="Total number of HTTP requests",
        labelnames=["tenant_id", "endpoint", "method", "status"],
        registry=isolated_registry,
    )


@pytest.fixture
def request_latency_histogram(isolated_registry: CollectorRegistry) -> Histogram:
    """
    Isolated request latency histogram for testing.

    METRIC: gravitea_request_latency_seconds
    LABELS: tenant_id, endpoint
    """
    return Histogram(
        name="gravitea_request_latency_seconds",
        documentation="Request latency in seconds",
        labelnames=["tenant_id", "endpoint"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=isolated_registry,
    )


@pytest.fixture
def gauge_test_helper():
    """
    Helper fixture for common gauge test operations.

    USAGE:
        def test_gauge_behavior(gauge_test_helper, orders_gauge, test_tenant):
            helper = gauge_test_helper(orders_gauge, {"tenant_id": str(test_tenant.id)})
            helper.assert_value(0)
            helper.increment()
            helper.assert_value(1)
    """

    class GaugeTestHelper:
        def __init__(self, gauge: Gauge, labels: dict):
            self.gauge = gauge
            self.labels = labels
            self._labeled = gauge.labels(**labels)

        def get_value(self) -> float:
            """Get current gauge value."""
            return self._labeled._value.get()

        def assert_value(self, expected: float, msg: str = None):
            """Assert gauge has expected value."""
            actual = self.get_value()
            assert actual == expected, msg or f"Expected {expected}, got {actual}"

        def increment(self, amount: float = 1):
            """Increment gauge by amount."""
            self._labeled.inc(amount)

        def decrement(self, amount: float = 1):
            """Decrement gauge by amount."""
            self._labeled.dec(amount)

        def set_value(self, value: float):
            """Set gauge to specific value."""
            self._labeled.set(value)

        def reset(self):
            """Reset gauge to 0."""
            self._labeled.set(0)

    def _factory(gauge: Gauge, labels: dict) -> GaugeTestHelper:
        return GaugeTestHelper(gauge, labels)

    return _factory


@pytest.fixture
def multi_tenant_gauge_scenario(
    isolated_registry: CollectorRegistry,
    orders_gauge: Gauge,
) -> dict:
    """
    Pre-configured multi-tenant gauge scenario for isolation testing.

    USAGE:
        def test_tenant_isolation(multi_tenant_gauge_scenario):
            tenant_a = multi_tenant_gauge_scenario["tenant_a"]
            tenant_b = multi_tenant_gauge_scenario["tenant_b"]
            gauge = multi_tenant_gauge_scenario["gauge"]

            # Verify operations on tenant_a don't affect tenant_b
    """
    tenant_a_id = "tenant-a-test-id"
    tenant_b_id = "tenant-b-test-id"

    return {
        "gauge": orders_gauge,
        "tenant_a": {
            "id": tenant_a_id,
            "labels": {"tenant_id": tenant_a_id},
        },
        "tenant_b": {
            "id": tenant_b_id,
            "labels": {"tenant_id": tenant_b_id},
        },
        "registry": isolated_registry,
    }
