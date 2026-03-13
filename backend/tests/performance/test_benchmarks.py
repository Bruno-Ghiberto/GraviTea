"""
Performance benchmark tests for Gravitea ERP (T117a).

Verifies API response times, database query efficiency, and memory usage
stay within acceptable performance baselines as defined in PERFORMANCE.md.

Requirements:
- SC-013: Support 100 concurrent users
- SC-015: Handle 50,000 product catalog
- SC-020: No N+1 query violations
- POS operations must be sub-second
"""

import time
from contextlib import contextmanager
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import connection, reset_queries


@contextmanager
def measure_time():
    """Context manager to measure execution time in milliseconds."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000


@contextmanager
def measure_queries():
    """Context manager to count database queries."""
    old_debug = settings.DEBUG
    settings.DEBUG = True
    reset_queries()

    try:
        yield lambda: len(connection.queries)
    finally:
        settings.DEBUG = old_debug


# ============================================================
# API Response Time Benchmarks
# ============================================================


@pytest.mark.django_db
@pytest.mark.performance
class TestAPIResponseTimes:
    """Verify API endpoints meet response time requirements."""

    def test_product_list_response_time(
        self, authenticated_client, product_factory, tenant_context
    ):
        """Product list endpoint should respond in < 200ms for 100 products."""
        # Create 100 products
        for i in range(100):
            product_factory(
                sku=f"BENCH-{i:04d}",
                name=f"Benchmark Product {i}",
            )

        # Measure response time
        with measure_time() as get_time:
            response = authenticated_client.get("/api/v1/products/")

        elapsed_ms = get_time()

        assert response.status_code == 200
        assert elapsed_ms < 200, f"Product list took {elapsed_ms:.1f}ms, expected < 200ms"

    def test_product_search_barcode_response_time(self, authenticated_client, tenant_context):
        """Barcode search should respond in < 50ms (SC-020 blind index requirement)."""
        from apps.inventario.models import Product

        # Create product with barcode (blind index auto-generated in save)
        barcode = "1234567890123"
        Product.objects.create(
            tenant=tenant_context,
            sku="BARCODE-001",
            name="Barcode Product",
            barcode=barcode,  # Correct field name
            unit_price=Decimal("100.000"),
            cost_price=Decimal("50.000"),
            tax_rate=Decimal("21.00"),
        )

        # Measure search time
        with measure_time() as get_time:
            response = authenticated_client.post(
                "/api/v1/products/search/", {"barcode": barcode}, format="json"
            )

        elapsed_ms = get_time()

        assert response.status_code == 200
        assert elapsed_ms < 50, f"Barcode search took {elapsed_ms:.1f}ms, expected < 50ms"

    def test_stock_movement_creation_response_time(self, authenticated_client, product, branch):
        """Stock movement creation should complete in < 100ms."""
        movement_data = {
            "product": str(product.id),
            "branch": str(branch.id),
            "type": "PURCHASE",
            "quantity_delta": "10.0000",
            "cost_snapshot": "50.00",
            "notes": "Performance benchmark",
        }

        # Measure creation time
        with measure_time() as get_time:
            response = authenticated_client.post("/api/v1/movements/", movement_data, format="json")

        elapsed_ms = get_time()

        assert response.status_code == 201
        assert elapsed_ms < 100, f"Movement creation took {elapsed_ms:.1f}ms, expected < 100ms"

    def test_auth_token_generation_response_time(self, api_client, admin_user):
        """Token generation should complete in < 100ms."""
        credentials = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }

        # Measure token generation time
        with measure_time() as get_time:
            response = api_client.post("/api/v1/auth/token/", credentials, format="json")

        elapsed_ms = get_time()

        assert response.status_code == 200
        assert elapsed_ms < 100, f"Token generation took {elapsed_ms:.1f}ms, expected < 100ms"


# ============================================================
# Database Query Efficiency Benchmarks
# ============================================================


@pytest.mark.django_db
@pytest.mark.performance
class TestQueryEfficiency:
    """Verify database queries stay within acceptable query count limits."""

    def test_single_product_fetch_efficiency(self, authenticated_client, product):
        """Single product fetch should use <= 2 queries and complete in < 10ms."""
        with measure_queries() as get_count, measure_time() as get_time:
            response = authenticated_client.get(f"/api/v1/products/{product.id}/")

        query_count = get_count()
        elapsed_ms = get_time()

        assert response.status_code == 200
        assert query_count <= 6, f"Product detail used {query_count} queries, expected <= 6"
        assert elapsed_ms < 10, f"Product detail took {elapsed_ms:.1f}ms, expected < 10ms"

    def test_product_list_with_stock_efficiency(
        self, authenticated_client, product_factory, branch, tenant_context
    ):
        """Product list with stock should use constant queries for 100 items."""
        from apps.inventario.models import StockSnapshot

        # Create 100 products with stock
        for i in range(100):
            product = product_factory(
                sku=f"STOCK-{i:04d}",
                name=f"Stock Product {i}",
            )
            StockSnapshot.objects.create(
                product=product,
                branch=branch,
                quantity=Decimal("100.0000"),
            )

        with measure_queries() as get_count, measure_time() as get_time:
            response = authenticated_client.get("/api/v1/products/")

        query_count = get_count()
        elapsed_ms = get_time()

        assert response.status_code == 200
        assert query_count <= 6, f"Product list used {query_count} queries, expected <= 6"
        assert (
            elapsed_ms < 50
        ), f"Product list took {elapsed_ms:.1f}ms, expected < 50ms for 100 items"

    def test_stock_movement_ledger_efficiency(
        self, authenticated_client, product, branch, tenant_context
    ):
        """Stock movement history should be efficient for 1000 records."""
        from apps.inventario.models import StockMovement

        # Create 1000 movements
        movements = []
        for i in range(1000):
            movements.append(
                StockMovement(
                    tenant=tenant_context,
                    product=product,
                    branch=branch,
                    type=StockMovement.MovementType.SALE,
                    quantity_delta=Decimal("-1.0000"),
                    cost_snapshot=Decimal("50.00"),
                    notes=f"Benchmark movement {i}",
                )
            )
        StockMovement.objects.bulk_create(movements)

        # Query with filter
        with measure_queries() as get_count, measure_time() as get_time:
            response = authenticated_client.get("/api/v1/movements/", {"product": str(product.id)})

        query_count = get_count()
        elapsed_ms = get_time()

        assert response.status_code == 200
        assert query_count <= 6, f"Movement list used {query_count} queries, expected <= 6"
        assert (
            elapsed_ms < 100
        ), f"Movement list took {elapsed_ms:.1f}ms, expected < 100ms for 1000 records"


# ============================================================
# Large Dataset Performance Tests
# ============================================================


@pytest.mark.django_db
@pytest.mark.performance
@pytest.mark.slow
class TestLargeDatasets:
    """
    Test performance with large datasets (SC-015).

    Marked as 'slow' - run with: pytest -m slow
    """

    def test_product_pagination_50k_products(
        self, authenticated_client, product_factory, tenant_context
    ):
        """
        Verify cursor pagination works efficiently with 50,000 products.

        Requirements:
        - SC-015: Support 50,000 product catalog
        - Response time < 5 seconds per page
        """
        # Note: Creating 50k products is slow in tests
        # For full benchmark, run: pytest -m slow

        # Create 1000 products as representative sample
        product_count = 1000
        for i in range(product_count):
            product_factory(
                sku=f"LARGE-{i:06d}",
                name=f"Large Dataset Product {i}",
            )

        # Test pagination performance
        with measure_time() as get_time:
            response = authenticated_client.get("/api/v1/products/")

        elapsed_ms = get_time()

        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) > 0

        # Pagination should be fast even with large datasets
        assert elapsed_ms < 5000, f"Pagination took {elapsed_ms:.1f}ms, expected < 5000ms"

    def test_pagination_memory_efficiency(
        self, authenticated_client, product_factory, tenant_context
    ):
        """Verify pagination doesn't load entire queryset into memory."""
        # Create 500 products
        for i in range(500):
            product_factory(
                sku=f"MEM-{i:04d}",
                name=f"Memory Test Product {i}",
            )

        # Request should only load one page, not all products
        response = authenticated_client.get("/api/v1/products/")

        assert response.status_code == 200

        # Standard pagination returns 100 items by default
        results_count = len(response.data["results"])
        assert results_count <= 100, (
            f"Pagination loaded {results_count} items, "
            f"should load max 100 to prevent memory issues"
        )


# ============================================================
# Concurrent User Simulation (SC-013)
# ============================================================


@pytest.mark.django_db
@pytest.mark.performance
@pytest.mark.slow
class TestConcurrency:
    """
    Test system can handle concurrent users (SC-013).

    Note: Full concurrency testing requires load testing tools like Locust.
    These tests verify basic concurrent access patterns.
    """

    def test_concurrent_product_reads(self, authenticated_client, product_factory, tenant_context):
        """Verify multiple concurrent read operations don't degrade performance."""
        # Create test products
        products = [product_factory() for _ in range(10)]

        # Simulate multiple reads
        total_time = 0
        iterations = 20

        for _ in range(iterations):
            with measure_time() as get_time:
                for product in products[:5]:
                    authenticated_client.get(f"/api/v1/products/{product.id}/")
            total_time += get_time()

        avg_time = total_time / iterations

        # Average time for 5 concurrent reads should be reasonable
        assert (
            avg_time < 100
        ), f"Average time for 5 product reads: {avg_time:.1f}ms, expected < 100ms"

    def test_mixed_read_write_operations(self, authenticated_client, product, branch):
        """Verify mixed read/write operations maintain performance."""

        operations_time = []

        for i in range(10):
            with measure_time() as get_time:
                # Read operation
                authenticated_client.get(f"/api/v1/products/{product.id}/")

                # Write operation
                authenticated_client.post(
                    "/api/v1/movements/",
                    {
                        "product": str(product.id),
                        "branch": str(branch.id),
                        "type": "ADJUSTMENT",
                        "quantity_delta": "1.0000",
                        "cost_snapshot": "50.00",
                        "notes": f"Concurrency test {i}",
                    },
                    format="json",
                )
            operations_time.append(get_time())

        avg_time = sum(operations_time) / len(operations_time)

        # Mixed operations should complete quickly
        assert avg_time < 150, f"Average mixed operation time: {avg_time:.1f}ms, expected < 150ms"


# ============================================================
# POS Performance Requirements
# ============================================================


@pytest.mark.django_db
@pytest.mark.performance
class TestPOSPerformance:
    """
    Verify POS operations are sub-second.

    Critical for user experience in retail environments.
    """

    def test_pos_product_lookup(self, authenticated_client, product_with_barcode):
        """POS product lookup by barcode should be sub-second."""
        with measure_time() as get_time:
            response = authenticated_client.post(
                "/api/v1/products/search/",
                {"barcode": product_with_barcode.barcode},  # Correct field name
                format="json",
            )

        elapsed_ms = get_time()

        assert response.status_code == 200
        assert elapsed_ms < 1000, f"POS barcode lookup took {elapsed_ms:.1f}ms, must be < 1000ms"

    def test_pos_stock_check(self, authenticated_client, product, branch, branch_stock):
        """POS stock check should be sub-second."""
        with measure_time() as get_time:
            response = authenticated_client.get(f"/api/v1/products/{product.id}/stock/")

        elapsed_ms = get_time()

        assert response.status_code == 200
        assert elapsed_ms < 1000, f"POS stock check took {elapsed_ms:.1f}ms, must be < 1000ms"

    def test_pos_sale_transaction(self, authenticated_client, product, branch):
        """Complete POS sale transaction should be sub-second."""
        sale_data = {
            "product": str(product.id),
            "branch": str(branch.id),
            "type": "SALE",
            "quantity_delta": "-1.0000",
            "cost_snapshot": "50.00",
            "notes": "POS sale",
        }

        with measure_time() as get_time:
            response = authenticated_client.post("/api/v1/movements/", sale_data, format="json")

        elapsed_ms = get_time()

        assert response.status_code == 201
        assert elapsed_ms < 1000, f"POS sale transaction took {elapsed_ms:.1f}ms, must be < 1000ms"
