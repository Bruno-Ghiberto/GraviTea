"""
T021 — Integration tests for the Field Definitions API endpoint.

Tests GET /api/v1/field-definitions/ for:
- Correct listing of active field definitions per tenant
- entity_type query-param filtering
- Exclusion of inactive definitions
- Ordering by section, position, field_key
- Tenant isolation (cross-tenant access returns empty list)
- 401 Unauthorized for unauthenticated requests
- Response schema contract validation
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)
from apps.core.models import TenantFieldDefinition, TenantModuleConfig

FIELD_DEFINITIONS_LIST_URL = reverse("field-definitions-list")


@pytest.mark.django_db
class TestFieldDefinitionsList:
    """T021: Tests for GET /api/v1/field-definitions/ list endpoint."""

    def test_list_returns_all_active_definitions_for_tenant(
        self, authenticated_client, tenant_context
    ):
        """Listing returns all active definitions belonging to the current tenant.

        Creates 3 active definitions and verifies all 3 are returned.
        """
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="peso_kg",
            label="Peso (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="marca",
            label="Marca",
            entity_type="product",
            field_type="text",
            section="caracteristicas",
            position=0,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="codigo_interno",
            label="Código Interno",
            entity_type="customer",
            field_type="text",
            section="custom_fields",
            position=0,
        )

        response = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        # DRF DefaultRouter may wrap in paginated response or return a plain list
        results = response.data.get("results", response.data)
        assert len(results) == 3

    def test_entity_type_filter_returns_only_matching_definitions(
        self, authenticated_client, tenant_context
    ):
        """?entity_type=product filters results to only product definitions.

        Creates one product definition and one customer definition;
        filtering by entity_type=product must return exactly 1 result.
        """
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="peso_kg",
            label="Peso (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="limite_credito",
            label="Límite de crédito",
            entity_type="customer",
            field_type="decimal",
            section="custom_fields",
            position=0,
        )

        response = authenticated_client.get(
            FIELD_DEFINITIONS_LIST_URL, {"entity_type": "product"}
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["entity_type"] == "product"
        assert results[0]["field_key"] == "peso_kg"

    def test_inactive_definitions_are_excluded(
        self, authenticated_client, tenant_context
    ):
        """Inactive field definitions must not appear in the listing.

        Creates one active and one inactive definition; response must contain
        only the active one.
        """
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="activo_field",
            label="Campo Activo",
            entity_type="product",
            field_type="text",
            section="custom_fields",
            position=0,
            active=True,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="inactivo_field",
            label="Campo Inactivo",
            entity_type="product",
            field_type="text",
            section="custom_fields",
            position=1,
            active=False,
        )

        response = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["field_key"] == "activo_field"

    def test_results_ordered_by_section_position_field_key(
        self, authenticated_client, tenant_context
    ):
        """Results are ordered by section ASC, position ASC, field_key ASC.

        Creates definitions in a scrambled order and verifies the response
        follows the declared model ordering.
        """
        # Create in reverse-expected order to detect ordering bugs
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="zzz_last",
            label="Z Last",
            entity_type="product",
            field_type="text",
            section="z_section",
            position=0,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="aaa_second",
            label="A Second",
            entity_type="product",
            field_type="text",
            section="a_section",
            position=1,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="aaa_first",
            label="A First",
            entity_type="product",
            field_type="text",
            section="a_section",
            position=0,
        )

        response = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 3
        assert results[0]["field_key"] == "aaa_first"   # section=a_section, position=0
        assert results[1]["field_key"] == "aaa_second"  # section=a_section, position=1
        assert results[2]["field_key"] == "zzz_last"    # section=z_section, position=0

    def test_tenant_isolation_other_tenant_sees_empty_list(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """Tenant A's field definitions are invisible to Tenant B.

        Creates a definition for Tenant A; Tenant B's authenticated client
        must receive an empty list (not a 403 — the endpoint returns 200 with
        filtered data per TenantBoundManager semantics).
        """
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="tenant_a_field",
            label="Tenant A Field",
            entity_type="product",
            field_type="text",
            section="custom_fields",
            position=0,
        )

        # Tenant A sees their own definition
        response_a = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)
        results_a = response_a.data.get("results", response_a.data)
        assert len(results_a) == 1

        # Temporarily switch thread-local context to other_tenant so the
        # view's get_queryset works correctly for other_tenant_client
        other_tenant = other_tenant_user.tenant
        set_current_tenant_id(other_tenant.id)
        try:
            response_b = other_tenant_client.get(FIELD_DEFINITIONS_LIST_URL)
        finally:
            set_current_tenant_id(tenant_context.id)

        assert response_b.status_code == status.HTTP_200_OK
        results_b = response_b.data.get("results", response_b.data)
        assert len(results_b) == 0

    def test_unauthenticated_request_returns_401(self, api_client):
        """GET /api/v1/field-definitions/ without a token must return 401."""
        response = api_client.get(FIELD_DEFINITIONS_LIST_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_response_schema_matches_contract(
        self, authenticated_client, tenant_context
    ):
        """Response fields match the declared serializer contract.

        Verifies every expected field is present in the response and no
        internal-only fields (like tenant or active) are leaked.
        """
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="material",
            label="Material",
            entity_type="product",
            field_type="select",
            section="caracteristicas",
            position=0,
            required=True,
            choices=["acero", "aluminio"],
            default_value="acero",
        )

        response = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1

        item = results[0]
        expected_fields = {
            "id",
            "field_key",
            "label",
            "entity_type",
            "field_type",
            "section",
            "position",
            "required",
            "default_value",
            "choices",
        }
        assert expected_fields == set(item.keys()), (
            f"Response keys {set(item.keys())} differ from contract {expected_fields}"
        )

        assert item["field_key"] == "material"
        assert item["label"] == "Material"
        assert item["entity_type"] == "product"
        assert item["field_type"] == "select"
        assert item["section"] == "caracteristicas"
        assert item["position"] == 0
        assert item["required"] is True
        assert item["choices"] == ["acero", "aluminio"]
        assert item["default_value"] == "acero"


MODULE_CONFIG_LIST_URL = reverse("module-config-list")


@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestTenantIsolationFieldDefinitions:
    """T036: Bidirectional tenant isolation for /field-definitions/ endpoint.

    Proves that Tenant A and Tenant B each see only their own field definitions
    in all directions — neither bleeds into the other.
    """

    def test_tenant_a_data_invisible_to_tenant_b(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """Tenant A's field definition is invisible to Tenant B.

        Creates a field definition owned by Tenant A and verifies that Tenant B,
        making an authenticated request with their own JWT, receives an empty list.
        """
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="peso_kg",
            label="Peso (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
        )

        # Tenant A sees their own field
        response_a = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)
        results_a = response_a.data.get("results", response_a.data)
        assert len(results_a) == 1
        assert results_a[0]["field_key"] == "peso_kg"

        # Switch thread-local to other_tenant — middleware handles RLS from JWT
        other_tenant = other_tenant_user.tenant
        set_current_tenant_id(other_tenant.id)
        try:
            response_b = other_tenant_client.get(FIELD_DEFINITIONS_LIST_URL)
        finally:
            set_current_tenant_id(tenant_context.id)

        assert response_b.status_code == status.HTTP_200_OK
        results_b = response_b.data.get("results", response_b.data)
        assert len(results_b) == 0, (
            "Tenant B must NOT see Tenant A's field definitions"
        )

    def test_tenant_b_data_invisible_to_tenant_a(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """Tenant B's field definition is invisible to Tenant A.

        Creates a field definition owned by Tenant B and verifies that Tenant A,
        making an authenticated request with their own JWT, receives an empty list.
        """
        other_tenant = other_tenant_user.tenant

        # Create field def under Tenant B (bypass TenantBoundManager by passing tenant= explicitly)
        # No need to switch thread-local for object creation — direct FK assignment bypasses the manager
        TenantFieldDefinition.objects.create(
            tenant=other_tenant,
            field_key="contact_code",
            label="Código de contacto",
            entity_type="customer",
            field_type="text",
            section="contacto",
            position=0,
        )

        # Tenant A sees empty list — Tenant B's field def does not bleed through
        response_a = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)
        results_a = response_a.data.get("results", response_a.data)
        assert len(results_a) == 0, (
            "Tenant A must NOT see Tenant B's field definitions"
        )

    def test_both_tenants_see_only_own_data_simultaneously(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """When both tenants have field definitions, each sees only their own.

        Tenant A has 2 definitions; Tenant B has 1 definition.
        Tenant A must get exactly 2; Tenant B must get exactly 1.
        This is the definitive bidirectional isolation proof.
        """
        other_tenant = other_tenant_user.tenant

        # Create 2 field defs for Tenant A
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="peso_kg",
            label="Peso (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
        )
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="material",
            label="Material",
            entity_type="product",
            field_type="text",
            section="caracteristicas",
            position=0,
        )

        # Create 1 field def for Tenant B (explicit tenant= bypasses TenantBoundManager)
        TenantFieldDefinition.objects.create(
            tenant=other_tenant,
            field_key="region_venta",
            label="Región de venta",
            entity_type="supplier",
            field_type="text",
            section="comercial",
            position=0,
        )

        # Tenant A sees exactly 2
        response_a = authenticated_client.get(FIELD_DEFINITIONS_LIST_URL)
        results_a = response_a.data.get("results", response_a.data)
        assert len(results_a) == 2, (
            f"Tenant A must see exactly 2 field defs, got {len(results_a)}"
        )
        tenant_a_keys = {item["field_key"] for item in results_a}
        assert tenant_a_keys == {"peso_kg", "material"}

        # Tenant B sees exactly 1
        set_current_tenant_id(other_tenant.id)
        try:
            response_b = other_tenant_client.get(FIELD_DEFINITIONS_LIST_URL)
        finally:
            set_current_tenant_id(tenant_context.id)

        results_b = response_b.data.get("results", response_b.data)
        assert len(results_b) == 1, (
            f"Tenant B must see exactly 1 field def, got {len(results_b)}"
        )
        assert results_b[0]["field_key"] == "region_venta"


@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestTenantIsolationModuleConfigViaFieldDefsFile:
    """T036: Bidirectional tenant isolation for /module-config/ endpoint.

    Verifies both endpoints in one place per T036 assignment:
    'Two tenants, each sees only own data via both endpoints.'
    """

    def test_both_tenants_see_only_own_module_configs_simultaneously(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """When both tenants have module configs, each sees only their own.

        Tenant A has 2 module configs (inventario enabled, sync disabled).
        Tenant B has 1 module config (ventas enabled).
        Each must see only their own records.
        """
        other_tenant = other_tenant_user.tenant

        # Tenant A's module configs
        TenantModuleConfig.objects.create(
            tenant=tenant_context,
            module="inventario",
            enabled=True,
        )
        TenantModuleConfig.objects.create(
            tenant=tenant_context,
            module="sync",
            enabled=False,
        )

        # Tenant B's module config (explicit tenant= bypasses TenantBoundManager)
        TenantModuleConfig.objects.create(
            tenant=other_tenant,
            module="ventas",
            enabled=True,
        )

        # Tenant A sees exactly 2 — their own inventario + sync
        response_a = authenticated_client.get(MODULE_CONFIG_LIST_URL)
        results_a = response_a.data.get("results", response_a.data)
        assert len(results_a) == 2, (
            f"Tenant A must see 2 module configs, got {len(results_a)}"
        )
        tenant_a_modules = {item["module"] for item in results_a}
        assert tenant_a_modules == {"inventario", "sync"}

        # Tenant B sees exactly 1 — their own ventas
        set_current_tenant_id(other_tenant.id)
        try:
            response_b = other_tenant_client.get(MODULE_CONFIG_LIST_URL)
        finally:
            set_current_tenant_id(tenant_context.id)

        results_b = response_b.data.get("results", response_b.data)
        assert len(results_b) == 1, (
            f"Tenant B must see exactly 1 module config, got {len(results_b)}"
        )
        assert results_b[0]["module"] == "ventas"


@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestCrossTenantValidationIsolation:
    """T036: Mixin validation must use the requesting tenant's field definitions.

    This proves the most critical isolation property: when Tenant B creates an
    entity, the CustomFieldsMixin validates custom_data against Tenant B's
    field definitions only — not Tenant A's.

    Failure mode: If the mixin leaked Tenant A's required field 'peso_kg',
    Tenant B's valid request (no peso_kg defined for them) would be incorrectly
    rejected with a validation error.
    """

    def test_tenant_b_validation_unaffected_by_tenant_a_field_definitions(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """Tenant A's required field does not contaminate Tenant B's validation.

        Setup:
        - Tenant A: required 'weight_kg' (decimal) on product
        - Tenant B: required 'color_code' (text) on product (different field)

        When Tenant B creates a product with 'color_code' but no 'weight_kg',
        the request must succeed — Tenant B's validator knows nothing of
        Tenant A's 'weight_kg' requirement.
        When Tenant A creates a product with 'weight_kg' but no 'color_code',
        the request must also succeed.
        """
        other_tenant = other_tenant_user.tenant

        # Tenant A gets required field 'weight_kg'
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            field_key="weight_kg",
            label="Weight (kg)",
            entity_type="product",
            field_type="decimal",
            section="dimensiones",
            position=0,
            required=True,
        )

        # Tenant B gets required field 'color_code' (entirely different — explicit FK bypasses manager)
        TenantFieldDefinition.objects.create(
            tenant=other_tenant,
            field_key="color_code",
            label="Color Code",
            entity_type="product",
            field_type="text",
            section="visual",
            position=0,
            required=True,
        )

        # Tenant A creates product with their required 'weight_kg', no 'color_code' → must succeed
        response_a = authenticated_client.post(
            "/api/v1/products/",
            {
                "sku": "TENANT-A-PROD-001",
                "name": "Tenant A Product",
                "custom_data": {"weight_kg": 5.5},
            },
            format="json",
        )
        assert response_a.status_code == status.HTTP_201_CREATED, (
            f"Tenant A product creation failed: {response_a.data}"
        )

        # Tenant B creates product with their required 'color_code', no 'weight_kg' → must succeed
        # (If mixin leaked Tenant A's definitions, this would incorrectly fail)
        set_current_tenant_id(other_tenant.id)
        try:
            response_b = other_tenant_client.post(
                "/api/v1/products/",
                {
                    "sku": "TENANT-B-PROD-001",
                    "name": "Tenant B Product",
                    "custom_data": {"color_code": "FF5733"},
                },
                format="json",
            )
        finally:
            set_current_tenant_id(tenant_context.id)

        assert response_b.status_code == status.HTTP_201_CREATED, (
            f"Tenant B product creation failed (possible cross-tenant validation bleed): {response_b.data}"
        )

    def test_tenant_a_validation_unaffected_by_tenant_b_field_definitions(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """Tenant B's required field does not contaminate Tenant A's validation.

        Inverse of the previous test — Tenant B's definitions must not appear
        in Tenant A's validation context.
        """
        other_tenant = other_tenant_user.tenant

        # Only Tenant B has any field definitions (Tenant A has none)
        # Explicit tenant= bypasses TenantBoundManager — no thread-local switch needed for ORM
        TenantFieldDefinition.objects.create(
            tenant=other_tenant,
            field_key="special_code",
            label="Special Code",
            entity_type="product",
            field_type="text",
            section="custom",
            position=0,
            required=True,
        )

        # Tenant A creates product with empty custom_data → must succeed because
        # Tenant A has NO field definitions, so nothing is required for them
        response_a = authenticated_client.post(
            "/api/v1/products/",
            {
                "sku": "TENANT-A-PROD-002",
                "name": "Tenant A No Custom Fields",
                "custom_data": {},
            },
            format="json",
        )
        assert response_a.status_code == status.HTTP_201_CREATED, (
            f"Tenant A product creation failed (Tenant B's required field bled into Tenant A): {response_a.data}"
        )
