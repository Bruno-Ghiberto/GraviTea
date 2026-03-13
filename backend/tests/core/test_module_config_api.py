"""
T032 — Integration tests for the Module Config API endpoint.

Tests GET /api/v1/module-config/ for:
- Correct listing of module configs with enabled/disabled status
- Tenant isolation (cross-tenant access returns empty list)
- 401 Unauthorized for unauthenticated requests
- Response schema contract validation (id, module, enabled, settings)
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import TenantModuleConfig

MODULE_CONFIG_LIST_URL = reverse("module-config-list")


@pytest.mark.django_db
class TestModuleConfigList:
    """T032: Tests for GET /api/v1/module-config/ list endpoint."""

    def test_list_returns_correct_modules_and_enabled_status(
        self, authenticated_client, tenant_context
    ):
        """Listing returns module configs with correct enabled/disabled status.

        Creates one enabled (inventario) and one disabled (sync) config and
        verifies both are returned with accurate enabled fields.
        """
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

        response = authenticated_client.get(MODULE_CONFIG_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 2

        # Build a lookup by module name for easier assertion
        by_module = {item["module"]: item for item in results}
        assert "inventario" in by_module
        assert "sync" in by_module
        assert by_module["inventario"]["enabled"] is True
        assert by_module["sync"]["enabled"] is False

    def test_tenant_isolation_other_tenant_sees_empty_list(
        self,
        authenticated_client,
        other_tenant_client,
        tenant_context,
        other_tenant_user,
    ):
        """Tenant A's module configs are invisible to Tenant B.

        Creates a module config for Tenant A; Tenant B's authenticated client
        must receive an empty list (200 with empty results, not 403).
        """
        TenantModuleConfig.objects.create(
            tenant=tenant_context,
            module="ventas",
            enabled=True,
        )

        # Tenant A sees their config
        response_a = authenticated_client.get(MODULE_CONFIG_LIST_URL)
        results_a = response_a.data.get("results", response_a.data)
        assert len(results_a) == 1

        # Temporarily switch thread-local context to other_tenant so the
        # view's get_queryset resolves correctly for the other tenant's JWT
        other_tenant = other_tenant_user.tenant
        set_current_tenant_id(other_tenant.id)
        try:
            response_b = other_tenant_client.get(MODULE_CONFIG_LIST_URL)
        finally:
            set_current_tenant_id(tenant_context.id)

        assert response_b.status_code == status.HTTP_200_OK
        results_b = response_b.data.get("results", response_b.data)
        assert len(results_b) == 0

    def test_unauthenticated_request_returns_401(self, api_client):
        """GET /api/v1/module-config/ without a token must return 401."""
        response = api_client.get(MODULE_CONFIG_LIST_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_response_schema_matches_contract(
        self, authenticated_client, tenant_context
    ):
        """Response fields match the declared serializer contract.

        Verifies id, module, enabled, and settings are present.
        Internal fields (tenant, created_at, updated_at) must not be exposed.
        """
        TenantModuleConfig.objects.create(
            tenant=tenant_context,
            module="facturacion",
            enabled=True,
            settings={"max_invoices_per_day": 500},
        )

        response = authenticated_client.get(MODULE_CONFIG_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1

        item = results[0]
        expected_fields = {"id", "module", "enabled", "settings"}
        assert expected_fields == set(item.keys()), (
            f"Response keys {set(item.keys())} differ from contract {expected_fields}"
        )

        assert item["module"] == "facturacion"
        assert item["enabled"] is True
        assert item["settings"] == {"max_invoices_per_day": 500}
        # id must be a non-empty string (UUID)
        assert item["id"] and isinstance(item["id"], str)
