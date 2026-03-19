"""API integration tests for acopio reference data endpoints."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestGrainTypeAPI:
    """GrainType API tests (AC-10-006, AC-10-007)."""

    def test_grain_types_list(self, authenticated_client, seed_grain_types) -> None:
        url = reverse("grain-type-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = response.json()
        # Paginated envelope
        assert "count" in data
        assert "next" in data
        assert "previous" in data
        assert "results" in data
        assert data["count"] >= 7

    def test_grain_types_detail(self, authenticated_client, seed_grain_types) -> None:
        from apps.acopio.models import GrainType

        trigo = GrainType.objects.get(code="TRI")
        url = reverse("grain-type-detail", args=[trigo.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "TRI"
        assert data["codigo"] == 15  # mapped from arca_codigo
        assert data["nombre"] == "Trigo pan"  # mapped from name

    def test_grain_types_filter_active(self, authenticated_client, seed_grain_types) -> None:
        url = reverse("grain-type-list")
        response = authenticated_client.get(url, {"is_active": "true"})
        assert response.status_code == 200
        for gt in response.json()["results"]:
            assert gt["is_active"] is True

    def test_grain_types_requires_auth(self, api_client, seed_grain_types) -> None:
        url = reverse("grain-type-list")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_grain_types_same_for_all_tenants(
        self, authenticated_client, other_tenant_client, seed_grain_types
    ) -> None:
        """AC-10-007: Global tables return same data for different tenants."""
        url = reverse("grain-type-list")
        resp_a = authenticated_client.get(url)
        resp_b = other_tenant_client.get(url)
        assert resp_a.json()["count"] == resp_b.json()["count"]


@pytest.mark.django_db
class TestCampanaConfigAPI:
    """CampanaConfig API tests (AC-10-006, AC-10-008)."""

    def test_campaigns_list_tenant_scoped(self, authenticated_client, campana_factory) -> None:
        campana_factory()
        url = reverse("campaign-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] >= 1

    def test_campaigns_create(self, authenticated_client) -> None:
        url = reverse("campaign-list")
        payload = {
            "campaign_code": "2025/26",
            "start_date": "2025-12-01",
            "end_date": "2026-11-30",
            "is_active": False,
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201

    def test_campaigns_cross_tenant_isolation(
        self, authenticated_client, other_tenant_client, campana_factory
    ) -> None:
        """AC-10-008: CampanaConfig returns different data per tenant."""
        campana_factory()  # Created for primary tenant
        url = reverse("campaign-list")
        # Primary tenant sees campaign
        resp_a = authenticated_client.get(url)
        assert resp_a.json()["count"] >= 1
        # Other tenant sees nothing
        resp_b = other_tenant_client.get(url)
        assert resp_b.json()["count"] == 0

    def test_campaigns_requires_auth(self, api_client) -> None:
        url = reverse("campaign-list")
        response = api_client.get(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestToleranceTableAPI:
    """ToleranceTable API tests (AC-10-006, AC-10-007)."""

    def test_tolerance_tables_list(self, authenticated_client, seed_grain_types) -> None:
        url = reverse("tolerance-table-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] > 0

    def test_tolerance_tables_filter_by_grain_type(
        self, authenticated_client, seed_grain_types
    ) -> None:
        from apps.acopio.models import GrainType

        trigo = GrainType.objects.get(code="TRI")
        url = reverse("tolerance-table-list")
        response = authenticated_client.get(url, {"grain_type": str(trigo.id)})
        assert response.status_code == 200
        for entry in response.json()["results"]:
            assert entry["grain_type"] == str(trigo.id)

    def test_tolerance_tables_same_for_all_tenants(
        self, authenticated_client, other_tenant_client, seed_grain_types
    ) -> None:
        url = reverse("tolerance-table-list")
        resp_a = authenticated_client.get(url)
        resp_b = other_tenant_client.get(url)
        assert resp_a.json()["count"] == resp_b.json()["count"]


@pytest.mark.django_db
class TestMermaTableAPI:
    """MermaTable API tests (AC-10-006, AC-10-007)."""

    def test_merma_tables_list(self, authenticated_client, seed_grain_types) -> None:
        url = reverse("merma-table-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.json()["count"] > 0

    def test_merma_tables_filter_by_grain_type(
        self, authenticated_client, seed_grain_types
    ) -> None:
        from apps.acopio.models import GrainType

        trigo = GrainType.objects.get(code="TRI")
        url = reverse("merma-table-list")
        response = authenticated_client.get(url, {"grain_type": str(trigo.id)})
        assert response.status_code == 200
        for entry in response.json()["results"]:
            assert entry["grain_type"] == str(trigo.id)

    def test_merma_tables_same_for_all_tenants(
        self, authenticated_client, other_tenant_client, seed_grain_types
    ) -> None:
        url = reverse("merma-table-list")
        resp_a = authenticated_client.get(url)
        resp_b = other_tenant_client.get(url)
        assert resp_a.json()["count"] == resp_b.json()["count"]
