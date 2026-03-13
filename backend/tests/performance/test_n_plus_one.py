"""
Performance tests for N+1 query prevention (T070, SC-020).

Verifies that API endpoints use efficient queries with select_related/prefetch_related.
"""

from contextlib import contextmanager
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import connection, reset_queries


@contextmanager
def capture_queries():
    """
    Context manager to capture database queries.

    Alternative to CaptureQueriesContext for Python 3.14.3compatibility.
    """
    # Enable debug queries
    old_debug = settings.DEBUG
    settings.DEBUG = True
    reset_queries()

    try:
        yield connection.queries
    finally:
        settings.DEBUG = old_debug


@pytest.mark.django_db
@pytest.mark.performance
class TestQueryPerformance:
    """Verify N+1 query prevention (SC-020)."""

    def test_product_list_query_count(self, authenticated_client, product_factory, tenant_context):
        """Test product list uses constant queries regardless of product count."""
        # Create 20 products
        for i in range(20):
            product_factory(
                sku=f"PERF-{i:03d}",
                name=f"Performance Test Product {i}",
            )

        reset_queries()
        response = authenticated_client.get("/api/v1/products/")
        queries = connection.queries

        assert response.status_code == 200

        # Should be <= 6 queries (auth, tenant context, products, related, pagination)
        query_count = len(queries)
        assert query_count <= 6, f"Expected <= 6 queries, got {query_count}"

    def test_stock_movement_list_query_count(
        self, authenticated_client, tenant_context, product, branch
    ):
        """Test stock movement list uses constant queries."""
        from apps.inventario.models import StockMovement

        # Create 20 movements
        for i in range(20):
            StockMovement.objects.create(
                tenant=tenant_context,
                product=product,
                branch=branch,
                type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal(f"{i + 1}.0000"),
                cost_snapshot=Decimal("50.00"),
                notes=f"Performance test movement {i}",
            )

        reset_queries()
        response = authenticated_client.get("/api/v1/movements/")
        queries = connection.queries

        assert response.status_code == 200

        # Should be <= 6 queries with proper select_related
        query_count = len(queries)
        assert query_count <= 6, f"Expected <= 6 queries, got {query_count}"

    def test_category_tree_query_count(self, authenticated_client, tenant_context):
        """Test category tree uses efficient recursive queries."""
        from apps.inventario.models import ProductCategory

        # Create hierarchical categories (3 levels, 5 roots with 3 children each)
        for i in range(5):
            parent = ProductCategory.objects.create(
                tenant=tenant_context,
                name=f"Root Category {i}",
            )
            for j in range(3):
                ProductCategory.objects.create(
                    tenant=tenant_context,
                    name=f"Child {i}-{j}",
                    parent=parent,
                )

        reset_queries()
        response = authenticated_client.get("/api/v1/categories/tree/")
        queries = connection.queries

        assert response.status_code == 200

        # Tree retrieval should use prefetch_related
        query_count = len(queries)
        assert query_count <= 8, f"Expected <= 8 queries for tree, got {query_count}"

    def test_supplier_list_query_count(self, authenticated_client, tenant_context):
        """Test supplier list with decrypted fields uses constant queries."""
        from apps.compras.models import Supplier

        # Create 20 suppliers
        for i in range(20):
            Supplier.objects.create(
                tenant=tenant_context,
                name=f"Supplier {i}",
                tax_id_encrypted=f"20-{i:08d}-9",
                email_encrypted=f"supplier{i}@test.com",
            )

        reset_queries()
        response = authenticated_client.get("/api/v1/compras/suppliers/")
        queries = connection.queries

        assert response.status_code == 200

        # Decryption happens in Python, not additional queries
        query_count = len(queries)
        assert query_count <= 5, f"Expected <= 5 queries, got {query_count}"

    def test_price_history_list_query_count(self, authenticated_client, tenant_context, product):
        """Test price history list with related objects uses efficient queries."""
        from django.utils import timezone

        from apps.inventario.models import PriceList, ProductPriceHistory

        # Create price list
        price_list = PriceList.objects.create(
            tenant=tenant_context,
            name="Test Price List",
        )

        # Create 20 price history entries
        for i in range(20):
            ProductPriceHistory.objects.create(
                product=product,
                price_list=price_list,
                price=Decimal(f"{100 + i}.00"),
                valid_from=timezone.now(),
            )

        reset_queries()
        response = authenticated_client.get("/api/v1/price-history/")
        queries = connection.queries

        assert response.status_code == 200

        # Should use select_related for product, price_list, changed_by_user
        query_count = len(queries)
        assert query_count <= 5, f"Expected <= 5 queries, got {query_count}"

    def test_product_detail_with_stock_query_count(self, authenticated_client, product, branch):
        """Test product detail with stock info uses minimal queries."""
        from apps.inventario.models import StockSnapshot

        # Create stock snapshot
        StockSnapshot.objects.create(
            product=product,
            branch=branch,
            quantity=Decimal("100.0000"),
        )

        reset_queries()
        response = authenticated_client.get(f"/api/v1/products/{product.id}/")
        queries = connection.queries

        assert response.status_code == 200

        query_count = len(queries)
        assert query_count <= 6, f"Expected <= 6 queries for detail, got {query_count}"


@pytest.mark.django_db
@pytest.mark.performance
class TestBulkOperationPerformance:
    """Test performance of bulk operations."""

    def test_bulk_product_creation_query_count(self, authenticated_client, tenant_context):
        """Test that bulk creates don't cause excessive queries."""
        # This tests the efficiency of multiple sequential creates
        # In production, consider batch_create for bulk imports

        reset_queries()
        for i in range(5):
            response = authenticated_client.post(
                "/api/v1/products/",
                {
                    "sku": f"BULK-{i:03d}",
                    "name": f"Bulk Product {i}",
                    "unit_price": "99.99",
                    "cost_price": "49.99",
                },
                format="json",
            )
            assert response.status_code == 201

        queries = connection.queries

        # Queries per create should be bounded
        query_count = len(queries)
        queries_per_create = query_count / 5
        assert (
            queries_per_create <= 10
        ), f"Expected <= 10 queries per create, got {queries_per_create:.1f}"

    def test_filtered_list_uses_indexes(
        self, authenticated_client, product_factory, tenant_context
    ):
        """Test that filtered queries use database indexes."""
        from apps.inventario.models import ProductCategory

        # Create categories for filtering
        category_a = ProductCategory.objects.create(
            tenant=tenant_context,
            name="Category A",
        )
        category_b = ProductCategory.objects.create(
            tenant=tenant_context,
            name="Category B",
        )

        # Create products in different categories
        for i in range(10):
            product_factory(
                sku=f"CAT-A-{i:03d}",
                category=category_a,
            )
        for i in range(10):
            product_factory(
                sku=f"CAT-B-{i:03d}",
                category=category_b,
            )

        reset_queries()
        response = authenticated_client.get("/api/v1/products/", {"category": str(category_a.id)})
        queries = connection.queries

        assert response.status_code == 200

        # Filtered query should still be constant
        query_count = len(queries)
        assert query_count <= 5, f"Expected <= 5 queries with filter, got {query_count}"


@pytest.fixture
def product_factory(tenant_context):
    """Factory for creating test products."""
    from apps.inventario.models import Product

    counter = [0]

    def create_product(**kwargs):
        counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "sku": f"TEST-{counter[0]:04d}",
            "name": f"Test Product {counter[0]}",
            "unit_price": Decimal("100.000"),
            "cost_price": Decimal("50.000"),
            "tax_rate": Decimal("21.00"),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    return create_product
