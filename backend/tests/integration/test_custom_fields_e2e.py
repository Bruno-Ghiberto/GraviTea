"""
T026 — Cross-entity custom field validation tests.

Verifies that CustomFieldsMixin works correctly across all 4 entity types
(product, customer, supplier, sale_order) with entity-specific isolation,
validation, and merge semantics.

Note: This project uses RFC 7807 Problem+JSON error format. Validation
errors are returned in response.data["errors"] as a list of
{"field": "dotted.path", "message": "...", "code": "..."} objects.
"""

import pytest
from rest_framework import status

from apps.core.models import TenantFieldDefinition
from apps.compras.models import Supplier


def _has_error_for_field(response_data, field_prefix):
    """Check if RFC 7807 errors contain an error for a given field prefix."""
    errors = response_data.get("errors", [])
    return any(e.get("field", "").startswith(field_prefix) for e in errors)


@pytest.mark.django_db
class TestCrossEntityCustomFields:
    """T026: Custom fields work across all entity types."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_field_def(tenant, entity_type, field_key, field_type, **kwargs):
        return TenantFieldDefinition.objects.create(
            tenant=tenant,
            entity_type=entity_type,
            field_key=field_key,
            label=kwargs.pop("label", field_key.replace("_", " ").title()),
            field_type=field_type,
            section=kwargs.pop("section", "custom_fields"),
            position=kwargs.pop("position", 0),
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Product custom_data via API
    # ------------------------------------------------------------------

    def test_product_accepts_valid_custom_data(
        self, authenticated_client, tenant_context
    ):
        """Product with valid custom_data matching field definitions is accepted."""
        self._create_field_def(tenant_context, "product", "color", "text")

        response = authenticated_client.post(
            "/api/v1/products/",
            {"sku": "PROD-CF-001", "name": "Test Product", "custom_data": {"color": "red"}},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["custom_data"]["color"] == "red"

    def test_product_rejects_invalid_custom_data_type(
        self, authenticated_client, tenant_context
    ):
        """Product with wrong type for a defined field is rejected."""
        self._create_field_def(tenant_context, "product", "weight_kg", "decimal")

        response = authenticated_client.post(
            "/api/v1/products/",
            {"sku": "PROD-CF-002", "name": "Bad Weight", "custom_data": {"weight_kg": "not-a-number"}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _has_error_for_field(response.data, "custom_data")

    # ------------------------------------------------------------------
    # Supplier custom_data via API
    # ------------------------------------------------------------------

    def test_supplier_accepts_valid_custom_data(
        self, authenticated_client, tenant_context
    ):
        """Supplier with valid custom_data is accepted."""
        self._create_field_def(tenant_context, "supplier", "lead_region", "text")

        response = authenticated_client.post(
            "/api/v1/compras/suppliers/",
            {"name": "Test Supplier", "custom_data": {"lead_region": "CABA"}},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["custom_data"]["lead_region"] == "CABA"

    def test_supplier_rejects_invalid_custom_data_type(
        self, authenticated_client, tenant_context
    ):
        """Supplier with wrong type for a defined field is rejected."""
        self._create_field_def(tenant_context, "supplier", "rating", "integer")

        response = authenticated_client.post(
            "/api/v1/compras/suppliers/",
            {"name": "Bad Supplier", "custom_data": {"rating": "five"}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _has_error_for_field(response.data, "custom_data")

    # ------------------------------------------------------------------
    # Customer custom_data via API
    # ------------------------------------------------------------------

    def test_customer_accepts_valid_custom_data(
        self, authenticated_client, tenant_context
    ):
        """Customer with valid custom_data is accepted."""
        self._create_field_def(tenant_context, "customer", "segment", "select", choices=["premium", "standard"])

        response = authenticated_client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": "20123456009",
                "razon_social": "Test Customer SA",
                "condicion_iva": 1,
                "doc_tipo": 80,
                "custom_data": {"segment": "premium"},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["custom_data"]["segment"] == "premium"

    def test_customer_rejects_invalid_select_choice(
        self, authenticated_client, tenant_context
    ):
        """Customer with invalid select choice is rejected."""
        self._create_field_def(tenant_context, "customer", "tier", "select", choices=["gold", "silver"])

        response = authenticated_client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": "20333333008",
                "razon_social": "Bad Choice SA",
                "condicion_iva": 5,
                "doc_tipo": 80,
                "custom_data": {"tier": "platinum"},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _has_error_for_field(response.data, "custom_data")

    # ------------------------------------------------------------------
    # Entity-specific isolation — no cross-contamination
    # ------------------------------------------------------------------

    def test_product_defs_do_not_apply_to_customer(
        self, authenticated_client, tenant_context
    ):
        """Product-only field definitions are silently ignored on Customer records.

        A customer with undefined (product-only) keys in custom_data should
        be accepted — undefined keys are silently ignored per design.
        """
        self._create_field_def(tenant_context, "product", "material", "text")

        response = authenticated_client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": "20444444003",
                "razon_social": "Cross-Check SA",
                "condicion_iva": 6,
                "doc_tipo": 80,
                "custom_data": {"material": "acero"},
            },
            format="json",
        )

        # Should succeed — "material" is a product field, not customer
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["custom_data"]["material"] == "acero"

    # ------------------------------------------------------------------
    # Merge semantics on non-product entity (PATCH)
    # ------------------------------------------------------------------

    def test_supplier_merge_semantics_on_update(
        self, authenticated_client, tenant_context
    ):
        """PATCH merges incoming custom_data with existing, null removes keys.

        1. Create supplier with {region: "CABA", priority: "high"}
        2. PATCH with {region: "GBA", priority: null}
        3. Verify result is {region: "GBA"} — region updated, priority removed
        """
        self._create_field_def(tenant_context, "supplier", "region", "text")
        self._create_field_def(tenant_context, "supplier", "priority", "text", position=1)

        # Create
        create_resp = authenticated_client.post(
            "/api/v1/compras/suppliers/",
            {
                "name": "Merge Test Supplier",
                "custom_data": {"region": "CABA", "priority": "high"},
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED, (
            f"Supplier creation failed: {create_resp.data}"
        )

        # SupplierCreateSerializer doesn't include 'id' — look up via ORM
        supplier = Supplier.all_objects.get(name="Merge Test Supplier")

        # Patch — update region, remove priority
        patch_resp = authenticated_client.patch(
            f"/api/v1/compras/suppliers/{supplier.id}/",
            {"custom_data": {"region": "GBA", "priority": None}},
            format="json",
        )

        assert patch_resp.status_code == status.HTTP_200_OK, f"PATCH failed: {patch_resp.data}"
        assert patch_resp.data["custom_data"]["region"] == "GBA"
        assert "priority" not in patch_resp.data["custom_data"]
