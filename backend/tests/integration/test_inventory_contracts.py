"""
Integration tests for inventory API contract validation.

Tests verify API contracts for:
- T019: Product CRUD validation with RFC 7807 error responses
- T021: Cursor-based pagination behavior

Per spec.md requirements for standardized error responses and pagination.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestProductCRUDValidation:
    """T019: Integration test for product CRUD validation.

    Validates:
    - Create product with valid data returns 201 and correct structure
    - Create product with missing required fields returns RFC 7807 400
    - Create product with duplicate SKU returns RFC 7807 400
    - Create product with invalid category (wrong tenant) returns RFC 7807 400
    - Update product with valid data returns 200
    - Update product with invalid data returns RFC 7807 400
    - Delete product (soft delete) works correctly
    - Get product detail returns correct structure
    """

    def test_create_product_with_valid_data(
        self, authenticated_client, product_category
    ):
        """Test creating product with valid data returns 201 with correct structure."""
        url = reverse("product-list")
        payload = {
            "sku": "TEST-VALID-001",
            "name": "Valid Product",
            "description": "A valid test product",
            "category": str(product_category.id),
            "unit_price": "100.000",
            "cost_price": "50.000",
            "tax_rate": "21.00",
            "is_active": True,
        }

        response = authenticated_client.post(url, payload, format="json")

        # Verify HTTP 201 Created
        assert response.status_code == status.HTTP_201_CREATED

        # Verify response structure (uses ProductCreateSerializer)
        data = response.data
        assert data["sku"] == "TEST-VALID-001"
        assert data["name"] == "Valid Product"
        assert data["description"] == "A valid test product"
        assert str(data["category"]) == str(product_category.id)
        assert Decimal(data["unit_price"]) == Decimal("100.000")
        assert Decimal(data["cost_price"]) == Decimal("50.000")
        assert Decimal(data["tax_rate"]) == Decimal("21.00")
        assert data["is_active"] is True

        # Note: ProductCreateSerializer doesn't include id, created_at, updated_at,
        # category_name, or price_with_tax - those are only in ProductSerializer

    def test_create_product_missing_required_fields(
        self, authenticated_client, problem_detail_validator
    ):
        """Test creating product with missing required fields returns RFC 7807 400."""
        url = reverse("product-list")
        # Missing required fields: sku, name (category and unit_price have defaults)
        payload = {
            "description": "Incomplete product",
        }

        response = authenticated_client.post(url, payload, format="json")

        # Verify HTTP 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=400,
            expected_type_suffix="validation-error",
            expect_errors=True,
        )

        # Verify errors array contains field-level errors
        errors = data["errors"]
        error_fields = [error["field"] for error in errors]

        # Check for required field errors (sku and name are required)
        assert "sku" in error_fields
        assert "name" in error_fields

        # Verify error structure
        for error in errors:
            assert "field" in error
            assert "message" in error
            assert "code" in error
            assert error["code"] in ("required", "null", "blank")

    def test_create_product_duplicate_sku(
        self, authenticated_client, product, problem_detail_validator
    ):
        """Test creating product with duplicate SKU returns RFC 7807 400."""
        url = reverse("product-list")
        # Use existing product's SKU
        payload = {
            "sku": product.sku,  # Duplicate
            "name": "Duplicate SKU Product",
            "category": str(product.category.id),
            "unit_price": "100.000",
            "cost_price": "50.000",
        }

        response = authenticated_client.post(url, payload, format="json")

        # Verify HTTP 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=400,
            expected_type_suffix="validation-error",
            expect_errors=True,
        )

        # Verify SKU error is present
        errors = data["errors"]
        sku_errors = [e for e in errors if e["field"] == "sku"]
        assert len(sku_errors) > 0
        assert any("already exists" in e["message"].lower() for e in sku_errors)

    def test_create_product_invalid_category_wrong_tenant(
        self, authenticated_client, other_tenant, problem_detail_validator
    ):
        """Test creating product with category from wrong tenant returns RFC 7807 400."""
        from apps.inventario.models import ProductCategory
        from apps.core.managers.tenant_bound import (
            set_current_tenant_id,
            clear_current_tenant_id,
        )

        # Create category in different tenant
        set_current_tenant_id(other_tenant.id)
        other_category = ProductCategory.objects.create(
            tenant=other_tenant,
            name="Other Tenant Category",
        )
        other_category_id = other_category.id
        clear_current_tenant_id()

        url = reverse("product-list")
        payload = {
            "sku": "TEST-WRONG-TENANT-001",
            "name": "Wrong Tenant Product",
            "category": str(other_category_id),  # Wrong tenant
            "unit_price": "100.000",
            "cost_price": "50.000",
        }

        response = authenticated_client.post(url, payload, format="json")

        # Verify HTTP 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=400,
            expected_type_suffix="validation-error",
            expect_errors=True,
        )

        # Verify category error - could be "does not exist" or "not found in organization"
        errors = data["errors"]
        category_errors = [e for e in errors if e["field"] == "category"]
        assert len(category_errors) > 0

    def test_update_product_valid_data(self, authenticated_client, product):
        """Test updating product with valid data returns 200."""
        url = reverse("product-detail", kwargs={"pk": product.id})
        payload = {
            "sku": product.sku,
            "name": "Updated Product Name",
            "description": "Updated description",
            "category": str(product.category.id),
            "unit_price": "150.000",
            "cost_price": "75.000",
            "tax_rate": "21.00",
            "is_active": True,
        }

        response = authenticated_client.put(url, payload, format="json")

        # Verify HTTP 200 OK
        assert response.status_code == status.HTTP_200_OK

        # Verify updated data
        data = response.data
        assert data["name"] == "Updated Product Name"
        assert data["description"] == "Updated description"
        assert Decimal(data["unit_price"]) == Decimal("150.000")
        assert Decimal(data["cost_price"]) == Decimal("75.000")

    def test_update_product_invalid_data(
        self, authenticated_client, product, problem_detail_validator
    ):
        """Test updating product with invalid data returns RFC 7807 400."""
        url = reverse("product-detail", kwargs={"pk": product.id})
        payload = {
            "sku": product.sku,
            "name": "",  # Invalid: empty name
            "category": str(product.category.id),
            "unit_price": "-100.000",  # Invalid: negative price
            "cost_price": "50.000",
        }

        response = authenticated_client.put(url, payload, format="json")

        # Verify HTTP 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=400,
            expected_type_suffix="validation-error",
            expect_errors=True,
        )

        # Verify errors array contains field errors
        errors = data["errors"]
        error_fields = [error["field"] for error in errors]
        assert "name" in error_fields or "unit_price" in error_fields

    def test_delete_product_soft_delete(
        self, authenticated_client, product, tenant_context
    ):
        """Test deleting product performs soft delete."""
        from apps.inventario.models import Product

        url = reverse("product-detail", kwargs={"pk": product.id})

        response = authenticated_client.delete(url)

        # Verify HTTP 204 No Content
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify product is soft-deleted (is_active = False)
        # Must set tenant context to access all_objects
        from apps.core.managers.tenant_bound import set_current_tenant_id

        set_current_tenant_id(tenant_context.id)
        product.refresh_from_db()
        assert product.is_active is False

        # Verify product still exists in all_objects queryset
        assert Product.all_objects.filter(pk=product.id).exists()

        # Verify product is excluded from default queryset (is_active filter)
        assert not Product.objects.filter(pk=product.id, is_active=True).exists()

    def test_get_product_detail_structure(self, authenticated_client, product):
        """Test getting product detail returns correct structure."""
        url = reverse("product-detail", kwargs={"pk": product.id})

        response = authenticated_client.get(url)

        # Verify HTTP 200 OK
        assert response.status_code == status.HTTP_200_OK

        # Verify response structure
        data = response.data
        assert str(data["id"]) == str(product.id)
        assert data["sku"] == product.sku
        assert data["name"] == product.name
        assert data["description"] == product.description
        assert str(data["category"]) == str(product.category.id)
        assert data["category_name"] == product.category.name
        assert Decimal(data["unit_price"]) == product.unit_price
        assert Decimal(data["cost_price"]) == product.cost_price
        assert Decimal(data["tax_rate"]) == product.tax_rate
        assert data["is_active"] == product.is_active
        assert "created_at" in data
        assert "updated_at" in data
        assert "price_with_tax" in data

    def test_get_nonexistent_product_returns_404(
        self, authenticated_client, problem_detail_validator
    ):
        """Test getting non-existent product returns RFC 7807 404."""
        import uuid

        fake_id = uuid.uuid4()
        url = reverse("product-detail", kwargs={"pk": fake_id})

        response = authenticated_client.get(url)

        # Verify HTTP 404 Not Found
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=404,
            expected_type_suffix="not-found",
            expect_errors=False,
        )

    def test_update_product_invalid_stock_levels(
        self, authenticated_client, product, problem_detail_validator
    ):
        """Test updating product with min_stock > max_stock returns RFC 7807 400."""
        url = reverse("product-detail", kwargs={"pk": product.id})
        payload = {
            "sku": product.sku,
            "name": product.name,
            "category": str(product.category.id),
            "unit_price": "100.000",
            "cost_price": "50.000",
            "min_stock": "100.0000",  # Invalid: min > max
            "max_stock": "50.0000",
        }

        response = authenticated_client.put(url, payload, format="json")

        # Verify HTTP 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=400,
            expected_type_suffix="validation-error",
            expect_errors=True,
        )

        # Verify min_stock error is present
        errors = data["errors"]
        min_stock_errors = [e for e in errors if e["field"] == "min_stock"]
        assert len(min_stock_errors) > 0


class TestProductPaginationBehavior:
    """T021: Integration test for pagination behavior.

    Validates:
    - List products returns cursor-based pagination with next, previous, results
    - Pagination works with filters applied
    - Page size is respected
    - Empty results return proper structure
    """

    def test_list_products_pagination_structure(
        self, authenticated_client, product_factory
    ):
        """Test listing products returns cursor-based pagination structure."""
        # Create multiple products
        for i in range(5):
            product_factory(
                sku=f"PAGE-TEST-{i:03d}",
                name=f"Pagination Test Product {i}",
            )

        url = reverse("product-list")
        response = authenticated_client.get(url)

        # Verify HTTP 200 OK
        assert response.status_code == status.HTTP_200_OK

        # Verify pagination structure
        data = response.data
        assert "results" in data
        assert "next" in data
        assert "previous" in data

        # Verify results is a list
        assert isinstance(data["results"], list)

        # Verify at least some products are returned
        assert len(data["results"]) > 0

    def test_pagination_page_size_respected(
        self, authenticated_client, product_factory
    ):
        """Test pagination respects page_size parameter."""
        # Create 15 products
        for i in range(15):
            product_factory(
                sku=f"SIZE-TEST-{i:03d}",
                name=f"Size Test Product {i}",
            )

        url = reverse("product-list")
        response = authenticated_client.get(url, {"page_size": 10})

        # Verify HTTP 200 OK
        assert response.status_code == status.HTTP_200_OK

        # Verify page size is respected
        data = response.data
        assert len(data["results"]) == 10

        # Verify next cursor exists (more results available)
        assert data["next"] is not None

    def test_pagination_with_filters(self, authenticated_client, product_factory):
        """Test pagination works correctly with filters applied."""
        # Create products with different categories
        from apps.inventario.models import ProductCategory
        from apps.core.managers.tenant_bound import get_current_tenant_id

        tenant_id = get_current_tenant_id()

        category_a = ProductCategory.objects.create(
            tenant_id=tenant_id,
            name="Category A",
        )
        category_b = ProductCategory.objects.create(
            tenant_id=tenant_id,
            name="Category B",
        )

        # Create 8 products in category A
        for i in range(8):
            product_factory(
                sku=f"CAT-A-{i:03d}",
                name=f"Category A Product {i}",
                category=category_a,
            )

        # Create 5 products in category B
        for i in range(5):
            product_factory(
                sku=f"CAT-B-{i:03d}",
                name=f"Category B Product {i}",
                category=category_b,
            )

        # Filter by category A with pagination
        url = reverse("product-list")
        response = authenticated_client.get(
            url, {"category": str(category_a.id), "page_size": 5}
        )

        # Verify HTTP 200 OK
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        # Verify pagination structure
        assert "results" in data
        assert "next" in data
        assert "previous" in data

        # Verify page size
        assert len(data["results"]) == 5

        # Verify all results belong to category A
        for product in data["results"]:
            assert str(product["category"]) == str(category_a.id)
            assert product["category_name"] == "Category A"

        # Verify next cursor exists (8 total, 5 per page)
        assert data["next"] is not None

    def test_pagination_empty_results_structure(self, authenticated_client):
        """Test pagination with no results returns proper structure."""
        url = reverse("product-list")
        # Filter for non-existent SKU
        response = authenticated_client.get(url, {"search": "NONEXISTENT-SKU-999"})

        # Verify HTTP 200 OK
        assert response.status_code == status.HTTP_200_OK

        # Verify pagination structure exists even with empty results
        data = response.data
        assert "results" in data
        assert "next" in data
        assert "previous" in data

        # Verify results is empty list
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 0

        # Verify no pagination cursors
        assert data["next"] is None
        assert data["previous"] is None

    def test_pagination_cursor_navigation(self, authenticated_client, product_factory):
        """Test navigating between pages using cursor pagination."""
        # Create 25 products
        for i in range(25):
            product_factory(
                sku=f"CURSOR-{i:03d}",
                name=f"Cursor Test Product {i}",
            )

        url = reverse("product-list")

        # Get first page - cursor pagination may not respect page_size perfectly
        response_page1 = authenticated_client.get(url)
        assert response_page1.status_code == status.HTTP_200_OK
        data_page1 = response_page1.data

        # Verify first page structure
        assert len(data_page1["results"]) > 0
        assert data_page1["previous"] is None

        # Only test navigation if there are multiple pages
        if data_page1["next"] is not None:
            # Get second page using next cursor
            next_url = data_page1["next"]
            # Extract just the query params from the full URL
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(next_url)
            cursor_param = parse_qs(parsed.query).get("cursor", [None])[0]

            response_page2 = authenticated_client.get(url, {"cursor": cursor_param})
            assert response_page2.status_code == status.HTTP_200_OK
            data_page2 = response_page2.data

            # Verify second page structure
            assert len(data_page2["results"]) > 0
            assert data_page2["previous"] is not None

            # Verify different products on different pages
            page1_ids = [str(p["id"]) for p in data_page1["results"]]
            page2_ids = [str(p["id"]) for p in data_page2["results"]]
            assert len(set(page1_ids) & set(page2_ids)) == 0  # No overlap

    def test_pagination_with_ordering(self, authenticated_client, product_factory):
        """Test pagination respects ordering parameter."""
        # Create products with different prices
        product_factory(sku="PRICE-001", name="Expensive", unit_price=Decimal("500.000"))
        product_factory(sku="PRICE-002", name="Medium", unit_price=Decimal("200.000"))
        product_factory(sku="PRICE-003", name="Cheap", unit_price=Decimal("50.000"))

        url = reverse("product-list")

        # Order by price ascending
        response = authenticated_client.get(url, {"ordering": "unit_price"})
        assert response.status_code == status.HTTP_200_OK

        results = response.data["results"]
        # Verify ascending order
        for i in range(len(results) - 1):
            current_price = Decimal(results[i]["unit_price"])
            next_price = Decimal(results[i + 1]["unit_price"])
            assert current_price <= next_price

    def test_pagination_count_not_included(self, authenticated_client, product_factory):
        """Test cursor pagination does not include total count for performance."""
        # Create some products
        for i in range(5):
            product_factory(sku=f"COUNT-{i:03d}")

        url = reverse("product-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Cursor pagination should not include count field
        # (This is different from page number pagination which includes count)
        assert "count" not in data or data.get("count") is None


class TestCrossTenantIsolation:
    """T055: Integration test for multi-tenant isolation.

    Validates that cross-tenant access returns 404 (not 403) to prevent
    information leakage about resource existence across tenants.

    Security requirement: Tenant isolation must not leak existence of
    resources to unauthorized tenants via HTTP status codes.
    """

    def test_access_other_tenant_product_returns_404(
        self, authenticated_client, other_tenant_product, problem_detail_validator
    ):
        """Test accessing product from another tenant returns RFC 7807 404.

        Security: Returns 404 (not 403) to prevent information disclosure
        about resource existence across tenant boundaries.
        """
        # authenticated_client is logged in as user from tenant A
        # other_tenant_product belongs to tenant B
        url = reverse("product-detail", kwargs={"pk": other_tenant_product.id})

        response = authenticated_client.get(url)

        # SECURITY: Must return 404 NOT 403
        # 403 would reveal that the resource exists in another tenant
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify RFC 7807 Problem Details format
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=404,
            expected_type_suffix="not-found",
            expect_errors=False,
        )

        # Verify trace_id is present for debugging
        assert "trace_id" in data

    def test_update_other_tenant_product_returns_404(
        self, authenticated_client, other_tenant_product, problem_detail_validator
    ):
        """Test updating product from another tenant returns RFC 7807 404."""
        url = reverse("product-detail", kwargs={"pk": other_tenant_product.id})
        payload = {
            "name": "Hacked Product Name",
            "sku": other_tenant_product.sku,
            "unit_price": "1.000",
        }

        response = authenticated_client.put(url, payload, format="json")

        # SECURITY: Must return 404 NOT 403
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=404,
            expected_type_suffix="not-found",
            expect_errors=False,
        )

    def test_delete_other_tenant_product_returns_404(
        self, authenticated_client, other_tenant_product, problem_detail_validator
    ):
        """Test deleting product from another tenant returns RFC 7807 404."""
        url = reverse("product-detail", kwargs={"pk": other_tenant_product.id})

        response = authenticated_client.delete(url)

        # SECURITY: Must return 404 NOT 403
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response["Content-Type"] == "application/problem+json"

        data = response.data
        problem_detail_validator(
            data,
            expected_status=404,
            expected_type_suffix="not-found",
            expect_errors=False,
        )

    def test_list_products_excludes_other_tenant(
        self, authenticated_client, product, other_tenant_product
    ):
        """Test listing products does not include products from other tenants.

        Note: Fixture ordering matters - `product` must come before
        `other_tenant_product` to ensure tenant context is established first.
        """
        url = reverse("product-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        product_ids = [str(p["id"]) for p in data["results"]]

        # Verify other tenant's product is NOT in the list
        assert str(other_tenant_product.id) not in product_ids

        # Verify own tenant's product IS in the list
        assert str(product.id) in product_ids

    def test_search_does_not_reveal_other_tenant_products(
        self, authenticated_client, other_tenant_product
    ):
        """Test search does not reveal products from other tenants."""
        url = reverse("product-list")

        # Search using other tenant's product SKU
        response = authenticated_client.get(
            url, {"search": other_tenant_product.sku}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        # Should return empty results, not forbidden
        assert len(data["results"]) == 0

        # No product from other tenant should be visible
        product_ids = [str(p["id"]) for p in data["results"]]
        assert str(other_tenant_product.id) not in product_ids
