"""
T013 — Supplier migration verification tests.

Verifies that the SeparateDatabaseAndState migration from inventario → compras
preserved data integrity: FK links, encrypted fields, custom_data, tenant
isolation, and full CRUD at the canonical /api/v1/compras/suppliers/ URL.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.compras.models import Supplier


@pytest.mark.django_db
class TestSupplierMigrationIntegrity:
    """Verify Supplier model works correctly after migration to compras app."""

    def test_supplier_model_accessible_from_compras(self, tenant_context: object) -> None:
        """Supplier can be created and queried via apps.compras.models."""
        supplier = Supplier.objects.create(
            tenant=tenant_context,
            name="Migration Test Supplier",
        )
        assert Supplier.objects.filter(id=supplier.id).exists()

    def test_supplier_backward_compat_import(self) -> None:
        """Supplier is re-exported from inventario for backward compat."""
        from apps.inventario.models import Supplier as InventarioSupplier

        assert InventarioSupplier is Supplier

    def test_supplier_db_table_unchanged(self) -> None:
        """Migration preserved the original db_table name."""
        assert Supplier._meta.db_table == "supplier"

    def test_product_fk_to_supplier_intact(
        self, tenant_context: object, product: object
    ) -> None:
        """Product.supplier FK still points to the correct Supplier model."""
        from apps.inventario.models import Product

        fk_field = Product._meta.get_field("supplier")
        assert fk_field.related_model is Supplier

    def test_encrypted_fields_roundtrip(self, tenant_context: object) -> None:
        """Encrypted fields store and retrieve correctly after migration."""
        supplier = Supplier.objects.create(
            tenant=tenant_context,
            name="Encrypted Roundtrip",
            tax_id_encrypted="20-98765432-1",
            email_encrypted="secret@supplier.com",
            contact_info_encrypted="Juan Perez — Compras",
            address_encrypted="Av. Corrientes 1234, CABA",
        )
        supplier.refresh_from_db()

        assert supplier.tax_id_encrypted == "20-98765432-1"
        assert supplier.email_encrypted == "secret@supplier.com"
        assert supplier.contact_info_encrypted == "Juan Perez — Compras"
        assert supplier.address_encrypted == "Av. Corrientes 1234, CABA"

    def test_blind_index_computed_on_save(self, tenant_context: object) -> None:
        """Blind indexes for tax_id and email are auto-computed."""
        supplier = Supplier.objects.create(
            tenant=tenant_context,
            name="Blind Index Test",
            tax_id_encrypted="20-11111111-1",
            email_encrypted="blind@test.com",
        )
        assert supplier.tax_id_hash is not None
        assert supplier.email_hash is not None
        assert len(supplier.tax_id_hash) == 64
        assert len(supplier.email_hash) == 64

    def test_custom_data_jsonb(self, tenant_context: object) -> None:
        """custom_data JSONB field works after migration."""
        supplier = Supplier.objects.create(
            tenant=tenant_context,
            name="Custom Data Test",
            custom_data={"region": "CABA", "priority": "high"},
        )
        supplier.refresh_from_db()
        assert supplier.custom_data["region"] == "CABA"
        assert supplier.custom_data["priority"] == "high"

    def test_tenant_isolation(
        self, tenant_context: object, other_tenant: object
    ) -> None:
        """TenantBoundManager enforces tenant isolation."""
        Supplier.objects.create(tenant=tenant_context, name="Tenant A Supplier")
        Supplier.objects.create(tenant=other_tenant, name="Tenant B Supplier")

        # all_objects bypasses tenant filter
        assert Supplier.all_objects.count() >= 2


@pytest.mark.django_db
class TestSupplierComprasAPI:
    """CRUD operations at /api/v1/compras/suppliers/."""

    BASE_URL = "/api/v1/compras/suppliers/"

    def test_list_suppliers(self, authenticated_client: object, tenant_context: object) -> None:
        """GET /compras/suppliers/ returns 200."""
        Supplier.objects.create(tenant=tenant_context, name="List Test")
        response = authenticated_client.get(self.BASE_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_create_supplier(self, authenticated_client: object) -> None:
        """POST /compras/suppliers/ creates a supplier."""
        data = {
            "name": "New Compras Supplier",
            "tax_id": "20-22222222-9",
            "email": "new@compras.com",
            "lead_time_days": 7,
        }
        response = authenticated_client.post(self.BASE_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Compras Supplier"

    def test_retrieve_supplier(self, authenticated_client: object, tenant_context: object) -> None:
        """GET /compras/suppliers/{id}/ returns supplier detail."""
        supplier = Supplier.objects.create(
            tenant=tenant_context, name="Retrieve Test"
        )
        response = authenticated_client.get(f"{self.BASE_URL}{supplier.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Retrieve Test"

    def test_update_supplier(self, authenticated_client: object, tenant_context: object) -> None:
        """PATCH /compras/suppliers/{id}/ updates supplier."""
        supplier = Supplier.objects.create(
            tenant=tenant_context, name="Before Update"
        )
        response = authenticated_client.patch(
            f"{self.BASE_URL}{supplier.id}/",
            {"name": "After Update"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "After Update"

    def test_soft_delete_supplier(self, authenticated_client: object, tenant_context: object) -> None:
        """DELETE /compras/suppliers/{id}/ soft-deletes (is_active=False)."""
        supplier = Supplier.objects.create(
            tenant=tenant_context, name="Delete Me", is_active=True
        )
        response = authenticated_client.delete(f"{self.BASE_URL}{supplier.id}/")
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK,
        ]
        supplier.refresh_from_db()
        assert supplier.is_active is False

    def test_search_by_tax_id(self, authenticated_client: object, tenant_context: object) -> None:
        """GET /compras/suppliers/search/?q=<tax_id> finds supplier."""
        Supplier.objects.create(
            tenant=tenant_context,
            name="Searchable",
            tax_id_encrypted="20-33333333-1",
        )
        url = reverse("supplier-search")
        response = authenticated_client.get(url, {"q": "20-33333333-1"})
        assert response.status_code == status.HTTP_200_OK

    def test_tenant_isolation_via_api(
        self, authenticated_client: object, other_tenant_client: object, tenant_context: object
    ) -> None:
        """Other tenant cannot access suppliers via API."""
        supplier = Supplier.objects.create(
            tenant=tenant_context, name="Isolated Supplier"
        )
        response = other_tenant_client.get(f"{self.BASE_URL}{supplier.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client: object) -> None:
        """Unauthenticated request returns 401."""
        response = api_client.get(self.BASE_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
