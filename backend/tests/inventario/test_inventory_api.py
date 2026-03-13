"""
Integration tests for Inventory API endpoints (T069).

Tests complete inventory API flow per contracts/inventory-api.yaml.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestProductAPI:
    """Test Product API endpoints."""

    def test_list_products(self, authenticated_client, product):
        """Test listing products returns paginated results."""
        url = reverse("product-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data or isinstance(response.data, list)

    def test_create_product(self, authenticated_client, tenant_context):
        """Test creating a product."""
        url = reverse("product-list")
        data = {
            "sku": "NEW-SKU-001",
            "name": "New Test Product",
            "unit_price": "199.990",
            "cost_price": "99.990",
            "tax_rate": "21.00",
            "is_active": True,
        }
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["sku"] == "NEW-SKU-001"
        assert response.data["name"] == "New Test Product"

    def test_get_product_detail(self, authenticated_client, product):
        """Test retrieving product details."""
        url = reverse("product-detail", kwargs={"pk": str(product.id)})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(product.id)
        assert response.data["sku"] == product.sku

    def test_get_product_by_barcode(self, authenticated_client, product_with_barcode):
        """Test barcode lookup endpoint."""
        url = reverse("product-search")
        response = authenticated_client.post(url, {"barcode": "1234567890123"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(product_with_barcode.id)

    def test_update_product(self, authenticated_client, product):
        """Test updating a product."""
        url = reverse("product-detail", kwargs={"pk": str(product.id)})
        data = {
            "name": "Updated Product Name",
            "unit_price": "299.990",
        }
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Product Name"

    def test_delete_product_soft_deletes(self, authenticated_client, product):
        """Test deleting a product (soft delete)."""
        url = reverse("product-detail", kwargs={"pk": str(product.id)})
        response = authenticated_client.delete(url)

        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]

    def test_tenant_isolation_other_tenant_cannot_access(self, other_tenant_client, product):
        """Test that users from other tenants cannot access products."""
        url = reverse("product-detail", kwargs={"pk": str(product.id)})
        response = other_tenant_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_request_returns_401(self, api_client):
        """Test that unauthenticated requests return 401."""
        url = reverse("product-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCategoryAPI:
    """Test Category API endpoints."""

    def test_list_categories(self, authenticated_client, tenant_context):
        """Test listing categories."""
        from apps.inventario.models import ProductCategory

        ProductCategory.objects.create(
            tenant=tenant_context,
            name="Test Category",
        )

        url = reverse("category-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_category(self, authenticated_client, tenant_context):
        """Test creating a category."""
        url = reverse("category-list")
        data = {
            "name": "Electronics",
        }
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Electronics"

    def test_create_category_with_parent(self, authenticated_client, tenant_context):
        """Test creating a category with parent."""
        from apps.inventario.models import ProductCategory

        parent = ProductCategory.objects.create(
            tenant=tenant_context,
            name="Parent Category",
        )

        url = reverse("category-list")
        data = {
            "name": "Child Category",
            "parent": str(parent.id),
        }
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data["parent"]) == str(parent.id)

    def test_get_category_tree(self, authenticated_client, tenant_context):
        """Test category tree endpoint."""
        from apps.inventario.models import ProductCategory

        parent = ProductCategory.objects.create(
            tenant=tenant_context,
            name="Parent",
        )
        ProductCategory.objects.create(
            tenant=tenant_context,
            name="Child",
            parent=parent,
        )

        url = reverse("category-tree")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSupplierAPI:
    """Test Supplier API endpoints with encrypted fields."""

    def test_create_supplier_with_pii(self, authenticated_client, tenant_context):
        """Test creating supplier with PII fields."""
        url = reverse("supplier-list")
        data = {
            "name": "Test Supplier Inc",
            "tax_id": "20-12345678-9",
            "email": "supplier@test.com",
            "contact_info": "John Doe - Sales Manager",
            "address": "123 Test Street, Buenos Aires",
            "lead_time_days": 5,
        }
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Test Supplier Inc"

    def test_search_supplier_by_tax_id(self, authenticated_client, tenant_context):
        """Test searching supplier by tax_id using blind index."""
        from apps.compras.models import Supplier

        Supplier.objects.create(
            tenant=tenant_context,
            name="Searchable Supplier",
            tax_id_encrypted="20-11111111-1",
        )

        url = reverse("supplier-search")
        response = authenticated_client.get(url, {"q": "20-11111111-1"})

        assert response.status_code == status.HTTP_200_OK

    def test_soft_delete_supplier(self, authenticated_client, tenant_context):
        """Test soft deleting supplier (sets is_active=False)."""
        from apps.compras.models import Supplier

        supplier = Supplier.objects.create(
            tenant=tenant_context,
            name="Deletable Supplier",
            is_active=True,
        )

        url = reverse("supplier-detail", kwargs={"pk": str(supplier.id)})
        response = authenticated_client.delete(url)

        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]

        supplier.refresh_from_db()
        assert supplier.is_active is False


@pytest.mark.django_db
class TestStockMovementAPI:
    """Test Stock Movement API endpoints."""

    def test_list_movements(self, authenticated_client, stock_movement):
        """Test listing stock movements."""
        url = reverse("movement-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_movement_via_api(self, authenticated_client, tenant_context, product, branch):
        """Test creating a stock movement via API."""
        url = reverse("movement-list")
        data = {
            "product": str(product.id),
            "branch": str(branch.id),
            "type": "PURCHASE",
            "quantity_delta": "50.0000",
            "cost_snapshot": "25.0000",
            "notes": "API test purchase",
        }
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    def test_movement_immutability_update_blocked(self, authenticated_client, stock_movement):
        """Test that stock movements cannot be updated."""
        url = reverse("movement-detail", kwargs={"pk": str(stock_movement.id)})
        data = {
            "notes": "Attempted update",
        }
        response = authenticated_client.patch(url, data, format="json")

        # Should be blocked by model or viewset
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_movement_immutability_delete_blocked(self, authenticated_client, stock_movement):
        """Test that stock movements cannot be deleted."""
        url = reverse("movement-detail", kwargs={"pk": str(stock_movement.id)})
        response = authenticated_client.delete(url)

        # Should be blocked by model or viewset
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestPriceListAPI:
    """Test Price List API endpoints."""

    def test_list_price_lists(self, authenticated_client, tenant_context):
        """Test listing price lists."""
        from apps.inventario.models import PriceList

        PriceList.objects.create(
            tenant=tenant_context,
            name="Retail",
            margin_pct=Decimal("30.00"),
        )

        url = reverse("pricelist-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_price_list(self, authenticated_client, tenant_context):
        """Test creating a price list."""
        url = reverse("pricelist-list")
        data = {
            "name": "Wholesale",
            "margin_pct": "15.00",
            "is_default": False,
        }
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Wholesale"

    def test_set_default_price_list(self, authenticated_client, tenant_context):
        """Test setting a price list as default."""
        from apps.inventario.models import PriceList

        price_list = PriceList.objects.create(
            tenant=tenant_context,
            name="To Be Default",
            is_default=False,
        )

        url = reverse("pricelist-set-default", kwargs={"pk": str(price_list.id)})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        price_list.refresh_from_db()
        assert price_list.is_default is True
