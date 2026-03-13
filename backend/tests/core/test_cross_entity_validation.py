"""
T026 — Cross-entity integration tests for CustomFieldsMixin validation.

Verifies that:
- Field definitions for one entity_type do NOT contaminate another
- Each serializer validates custom_data only against its own entity_type
- Custom data passes through create/update for all 4 entity types
- Mixin validate chain works through serializer MRO (super().validate())
- Cache key isolation by entity_type prevents cross-contamination
"""

import pytest
from unittest import mock

from rest_framework import serializers

from apps.core.models import TenantFieldDefinition
from apps.core.serializers.customization import CustomFieldsMixin


# ---------------------------------------------------------------
# Minimal test serializers that mirror production MRO patterns
# ---------------------------------------------------------------

class _FakeModel:
    """Lightweight stand-in so DRF Meta.model can resolve fields."""
    _meta = type("FakeMeta", (), {
        "get_fields": lambda self: [],
        "fields_map": {},
        "many_to_many": [],
        "related_objects": [],
        "app_label": "test",
        "model_name": "fake",
    })()


class ProductMixinSerializer(CustomFieldsMixin, serializers.Serializer):
    entity_type = "product"
    name = serializers.CharField()
    custom_data = serializers.JSONField(default=dict, required=False)


class SupplierMixinSerializer(CustomFieldsMixin, serializers.Serializer):
    entity_type = "supplier"
    name = serializers.CharField()
    custom_data = serializers.JSONField(default=dict, required=False)


class CustomerMixinSerializer(CustomFieldsMixin, serializers.Serializer):
    entity_type = "customer"
    name = serializers.CharField()
    custom_data = serializers.JSONField(default=dict, required=False)


class SaleOrderMixinSerializer(CustomFieldsMixin, serializers.Serializer):
    entity_type = "sale_order"
    name = serializers.CharField()
    custom_data = serializers.JSONField(default=dict, required=False)


# ---------------------------------------------------------------
# Tests
# ---------------------------------------------------------------

@pytest.mark.django_db
class TestCrossEntityFieldIsolation:
    """T026: Field definitions for one entity must NOT affect another."""

    def test_product_field_does_not_apply_to_supplier(self, tenant_context):
        """A product-scoped field definition must be invisible to supplier validation."""
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="peso_kg",
            label="Peso (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
            required=True,
        )

        # Supplier serializer should NOT require peso_kg
        ser = SupplierMixinSerializer(data={"name": "Test Supplier", "custom_data": {}})
        ser.context["request"] = _make_request(tenant_context)
        assert ser.is_valid(), f"Supplier should be valid: {ser.errors}"

    def test_supplier_field_does_not_apply_to_product(self, tenant_context):
        """A supplier-scoped field definition must be invisible to product validation."""
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="contact_person",
            label="Contact Person",
            entity_type="supplier",
            field_type="text",
            section="contacto",
            position=0,
            required=True,
        )

        # Product serializer should NOT require contact_person
        ser = ProductMixinSerializer(data={"name": "Test Product", "custom_data": {}})
        ser.context["request"] = _make_request(tenant_context)
        assert ser.is_valid(), f"Product should be valid: {ser.errors}"

    def test_customer_field_does_not_apply_to_sale_order(self, tenant_context):
        """A customer-scoped field definition must be invisible to sale_order validation."""
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="limite_credito",
            label="Credit Limit",
            entity_type="customer",
            field_type="decimal",
            section="financiero",
            position=0,
            required=True,
        )

        # SaleOrder serializer should NOT require limite_credito
        ser = SaleOrderMixinSerializer(data={"name": "Test Order", "custom_data": {}})
        ser.context["request"] = _make_request(tenant_context)
        assert ser.is_valid(), f"SaleOrder should be valid: {ser.errors}"

    def test_each_entity_validates_only_its_own_fields(self, tenant_context):
        """Create definitions for all 4 entity types; each serializer validates only its own."""
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="product_field",
            label="Product Field",
            entity_type="product",
            field_type="text",
            section="custom",
            position=0,
            required=True,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="supplier_field",
            label="Supplier Field",
            entity_type="supplier",
            field_type="text",
            section="custom",
            position=0,
            required=True,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="customer_field",
            label="Customer Field",
            entity_type="customer",
            field_type="text",
            section="custom",
            position=0,
            required=True,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="order_field",
            label="Order Field",
            entity_type="sale_order",
            field_type="text",
            section="custom",
            position=0,
            required=True,
        )

        request = _make_request(tenant_context)

        # Product — supply only product_field, omit the rest
        ser = ProductMixinSerializer(
            data={"name": "Prod", "custom_data": {"product_field": "ok"}}
        )
        ser.context["request"] = request
        assert ser.is_valid(), f"Product failed: {ser.errors}"

        # Supplier — supply only supplier_field
        ser = SupplierMixinSerializer(
            data={"name": "Sup", "custom_data": {"supplier_field": "ok"}}
        )
        ser.context["request"] = request
        assert ser.is_valid(), f"Supplier failed: {ser.errors}"

        # Customer — supply only customer_field
        ser = CustomerMixinSerializer(
            data={"name": "Cust", "custom_data": {"customer_field": "ok"}}
        )
        ser.context["request"] = request
        assert ser.is_valid(), f"Customer failed: {ser.errors}"

        # SaleOrder — supply only order_field
        ser = SaleOrderMixinSerializer(
            data={"name": "Order", "custom_data": {"order_field": "ok"}}
        )
        ser.context["request"] = request
        assert ser.is_valid(), f"SaleOrder failed: {ser.errors}"


@pytest.mark.django_db
class TestCacheKeyIsolation:
    """T026: Cache keys must isolate by entity_type to prevent contamination."""

    def test_cache_key_scopes_by_entity_type(self, tenant_context):
        """Requesting field defs for product vs supplier must use different cache keys."""
        captured_keys = []

        def fake_get(key):
            captured_keys.append(key)
            return None

        with mock.patch("apps.core.serializers.customization.cache.get", side_effect=fake_get), \
             mock.patch("apps.core.serializers.customization.cache.set"):
            CustomFieldsMixin._get_field_definitions(tenant_context.id, "product")
            CustomFieldsMixin._get_field_definitions(tenant_context.id, "supplier")

        assert len(captured_keys) == 2
        assert captured_keys[0] != captured_keys[1], (
            "Cache keys for different entity_types must differ"
        )
        assert "product" in captured_keys[0]
        assert "supplier" in captured_keys[1]


@pytest.mark.django_db
class TestMixinValidateChain:
    """T026: CustomFieldsMixin.validate must be reachable through the MRO."""

    def test_mixin_validate_called_when_subclass_calls_super(self, tenant_context):
        """Serializer that calls super().validate() triggers mixin validation."""
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="peso_kg",
            label="Peso (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
            required=True,
        )

        class ChainedSerializer(CustomFieldsMixin, serializers.Serializer):
            entity_type = "product"
            name = serializers.CharField()
            custom_data = serializers.JSONField(default=dict, required=False)

            def validate(self, attrs):
                # Custom logic here, then chain to mixin
                return super().validate(attrs)

        ser = ChainedSerializer(data={"name": "Test", "custom_data": {}})
        ser.context["request"] = _make_request(tenant_context)
        # Should fail because required field peso_kg is missing
        assert not ser.is_valid()
        assert "custom_data" in ser.errors

    def test_mixin_validate_accepts_valid_custom_data(self, tenant_context):
        """When required custom data is provided, validation passes."""
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="material",
            label="Material",
            entity_type="product",
            field_type="select",
            section="custom",
            position=0,
            required=True,
            choices=["acero", "aluminio", "bronce"],
        )

        ser = ProductMixinSerializer(
            data={"name": "Test", "custom_data": {"material": "acero"}}
        )
        ser.context["request"] = _make_request(tenant_context)
        assert ser.is_valid(), f"Unexpected errors: {ser.errors}"


# ---------------------------------------------------------------
# Helper
# ---------------------------------------------------------------

def _make_request(tenant):
    """Create a minimal mock request with tenant context for serializer validation."""
    user = mock.Mock()
    user.tenant = tenant
    user.tenant_id = tenant.id
    request = mock.Mock()
    request.user = user
    return request
