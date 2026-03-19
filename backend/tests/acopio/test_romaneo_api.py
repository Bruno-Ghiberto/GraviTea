"""API integration tests for Romaneo and QualityAnalysis endpoints.

Covers the full lifecycle through the REST API:
- CRUD: create, list, detail, partial update
- State transitions: confirmar-arribo, peso-bruto, analizar, confirmar, tara, cerrar
- Merma preview (non-persisting)
- Nested QualityAnalysis CRUD with state guards
- Tenant isolation (cross-tenant returns 404 / empty list)
- Immutability enforcement (409 on CONFORME/CERRADO edits)
"""

import uuid
from decimal import Decimal

import pytest


@pytest.mark.django_db
class TestRomaneoCreateAPI:
    """POST /api/v1/acopio/romaneos/ -- create romaneo."""

    def test_create_romaneo_201(self, authenticated_client, romaneo_factory):
        """POST creates romaneo in PENDIENTE with auto-generated number."""
        # Create one romaneo to get shared FK IDs
        r = romaneo_factory()

        response = authenticated_client.post(
            "/api/v1/acopio/romaneos/",
            {
                "grain_type": str(r.grain_type_id),
                "campaign": str(r.campaign_id),
                "branch": str(r.branch_id),
                "patente_chasis": "ZZ999AA",
                "driver_name": "API Test Driver",
                "driver_dni": "99999999",
                "cpe_numero": f"CPE-API-{uuid.uuid4().hex[:6]}",
                "producer_cuit": "20999888777",
                "origin_locality": "Rosario, Santa Fe",
                "operator_id": str(r.operator_id_id),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == "PENDIENTE"
        assert response.data["romaneo_number"].startswith("ROM-")

    def test_create_romaneo_unauthenticated_401(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.post(
            "/api/v1/acopio/romaneos/", {}, format="json"
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestRomaneoListAPI:
    """GET /api/v1/acopio/romaneos/ -- paginated list."""

    def test_list_paginated(self, authenticated_client, romaneo_factory):
        """List returns paginated results."""
        for _ in range(3):
            romaneo_factory()
        response = authenticated_client.get("/api/v1/acopio/romaneos/")
        assert response.status_code == 200
        assert "results" in response.data
        assert response.data["count"] >= 3

    def test_tenant_isolation(
        self, authenticated_client, other_tenant_client, romaneo_factory
    ):
        """Cross-tenant access returns empty list, not other tenant's data."""
        romaneo_factory()  # created in default tenant

        response = other_tenant_client.get("/api/v1/acopio/romaneos/")
        assert response.status_code == 200
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestRomaneoDetailAPI:
    """GET /api/v1/acopio/romaneos/{id}/ -- detail with nested QA+MC."""

    def test_retrieve_with_nested(self, authenticated_client, romaneo_analizado):
        """Detail includes quality_analysis (populated) and merma_calculation (null)."""
        response = authenticated_client.get(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/"
        )
        assert response.status_code == 200
        assert response.data["quality_analysis"] is not None
        assert response.data["merma_calculation"] is None  # Not yet confirmed

    def test_cross_tenant_404(self, other_tenant_client, romaneo_factory):
        """Other tenant cannot access this tenant's romaneo."""
        r = romaneo_factory()
        response = other_tenant_client.get(
            f"/api/v1/acopio/romaneos/{r.pk}/"
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestRomaneoUpdateAPI:
    """PATCH /api/v1/acopio/romaneos/{id}/ -- partial update."""

    def test_patch_pendiente_200(self, authenticated_client, romaneo_factory):
        """PATCH on PENDIENTE succeeds."""
        r = romaneo_factory()
        response = authenticated_client.patch(
            f"/api/v1/acopio/romaneos/{r.pk}/",
            {"driver_name": "Updated Name"},
            format="json",
        )
        assert response.status_code == 200

    def test_patch_conforme_409(self, authenticated_client, romaneo_factory):
        """PATCH on CONFORME returns 409 romaneo_immutable."""
        from apps.acopio.models import Romaneo

        r = romaneo_factory()
        for s in [
            Romaneo.RomaneoStatus.EN_PROCESO,
            Romaneo.RomaneoStatus.PESADO,
            Romaneo.RomaneoStatus.ANALIZADO,
            Romaneo.RomaneoStatus.CONFORME,
        ]:
            r.status = s
            r.save()

        response = authenticated_client.patch(
            f"/api/v1/acopio/romaneos/{r.pk}/",
            {"driver_name": "Blocked"},
            format="json",
        )
        assert response.status_code == 409
        assert response.data["type"] == "romaneo_immutable"

    def test_patch_cerrado_409(self, authenticated_client, romaneo_factory):
        """PATCH on CERRADO also returns 409 romaneo_immutable."""
        from apps.acopio.models import Romaneo

        r = romaneo_factory()
        for s in [
            Romaneo.RomaneoStatus.EN_PROCESO,
            Romaneo.RomaneoStatus.PESADO,
            Romaneo.RomaneoStatus.ANALIZADO,
            Romaneo.RomaneoStatus.CONFORME,
            Romaneo.RomaneoStatus.CERRADO,
        ]:
            r.status = s
            r.save()

        response = authenticated_client.patch(
            f"/api/v1/acopio/romaneos/{r.pk}/",
            {"driver_name": "Blocked"},
            format="json",
        )
        assert response.status_code == 409
        assert response.data["type"] == "romaneo_immutable"


@pytest.mark.django_db
class TestStateTransitionAPIs:
    """State transition action endpoints."""

    def test_confirmar_arribo_202(self, authenticated_client, romaneo_factory):
        """PENDIENTE -> EN_PROCESO returns 202."""
        r = romaneo_factory()
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{r.pk}/confirmar-arribo/"
        )
        assert response.status_code == 202

    def test_peso_bruto_200(self, authenticated_client, romaneo_en_proceso):
        """EN_PROCESO -> PESADO with peso_bruto_kg returns 200."""
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_en_proceso.pk}/peso-bruto/",
            {"peso_bruto_kg": "30000.000"},
            format="json",
        )
        assert response.status_code == 200

    def test_analizar_200(self, authenticated_client, romaneo_pesado):
        """PESADO -> ANALIZADO with QA data returns 200."""
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_pesado.pk}/analizar/",
            {
                "humedad_pct": "15.20",
                "materias_extranas_pct": "1.80",
                "granos_danados_pct": "2.00",
                "granos_quebrados_pct": "3.00",
                "granos_ardidos_pct": "0.50",
                "cuerpos_extranos_pct": "0.10",
            },
            format="json",
        )
        assert response.status_code == 200

    def test_confirmar_200(
        self,
        authenticated_client,
        romaneo_analizado,
        merma_table_factory,
        tolerance_table_factory,
        storage_unit_factory,
    ):
        """ANALIZADO -> CONFORME creates MermaCalculation."""
        merma_table_factory(romaneo_analizado.grain_type)
        tolerance_table_factory(romaneo_analizado.grain_type)

        # Spec-12: storage_unit must be assigned before confirmar
        unit = storage_unit_factory(branch=romaneo_analizado.branch)
        romaneo_analizado.storage_unit = unit
        romaneo_analizado.save(update_fields=["storage_unit_id"])

        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/confirmar/",
            {"grado_asignado": 1},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "CONFORME"
        assert response.data["merma_calculation"] is not None

    def test_tara_200(
        self,
        authenticated_client,
        romaneo_analizado,
        merma_table_factory,
        tolerance_table_factory,
        storage_unit_factory,
    ):
        """Tara capture while CONFORME computes peso_neto_bruto_kg."""
        merma_table_factory(romaneo_analizado.grain_type)
        tolerance_table_factory(romaneo_analizado.grain_type)

        # Spec-12: storage_unit must be assigned before confirmar
        unit = storage_unit_factory(branch=romaneo_analizado.branch)
        romaneo_analizado.storage_unit = unit
        romaneo_analizado.save(update_fields=["storage_unit_id"])

        # First confirm to CONFORME
        authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/confirmar/",
            {"grado_asignado": 1},
            format="json",
        )

        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/tara/",
            {"tara_kg": "12000.000"},
            format="json",
        )
        assert response.status_code == 200
        assert Decimal(response.data["peso_neto_bruto_kg"]) == Decimal("18000.000")

    def test_cerrar_202(
        self,
        authenticated_client,
        romaneo_analizado,
        merma_table_factory,
        tolerance_table_factory,
        storage_unit_factory,
    ):
        """CONFORME -> CERRADO after tara returns 202."""
        merma_table_factory(romaneo_analizado.grain_type)
        tolerance_table_factory(romaneo_analizado.grain_type)

        # Spec-12: storage_unit must be assigned before confirmar
        unit = storage_unit_factory(branch=romaneo_analizado.branch)
        romaneo_analizado.storage_unit = unit
        romaneo_analizado.save(update_fields=["storage_unit_id"])

        authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/confirmar/",
            {"grado_asignado": 1},
            format="json",
        )
        authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/tara/",
            {"tara_kg": "12000.000"},
            format="json",
        )

        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/cerrar/"
        )
        assert response.status_code == 202
        assert response.data["status"] == "CERRADO"

    def test_invalid_transition_409(self, authenticated_client, romaneo_factory):
        """Out-of-sequence transition returns 409 with error details."""
        r = romaneo_factory()
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{r.pk}/peso-bruto/",
            {"peso_bruto_kg": "30000.000"},
            format="json",
        )
        assert response.status_code == 409
        assert response.data["type"] == "invalid_state_transition"
        assert "current_status" in response.data

    def test_cerrar_without_tara_400(
        self,
        authenticated_client,
        romaneo_analizado,
        merma_table_factory,
        tolerance_table_factory,
        storage_unit_factory,
    ):
        """Cerrar without tara_kg returns 400."""
        merma_table_factory(romaneo_analizado.grain_type)
        tolerance_table_factory(romaneo_analizado.grain_type)

        # Spec-12: storage_unit must be assigned before confirmar
        unit = storage_unit_factory(branch=romaneo_analizado.branch)
        romaneo_analizado.storage_unit = unit
        romaneo_analizado.save(update_fields=["storage_unit_id"])

        authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/confirmar/",
            {"grado_asignado": 1},
            format="json",
        )
        # Skip tara, try to close directly
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/cerrar/"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestMermaPreviewAPI:
    """GET /api/v1/acopio/romaneos/{id}/merma-preview/ -- non-persisting preview."""

    def test_preview_200(
        self, authenticated_client, romaneo_analizado, merma_table_factory
    ):
        """Preview returns merma results for ANALIZADO romaneo."""
        merma_table_factory(romaneo_analizado.grain_type)
        response = authenticated_client.get(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/merma-preview/"
        )
        assert response.status_code == 200
        assert "peso_final_kg" in response.data
        assert "total_merma_kg" in response.data

    def test_preview_wrong_state_409(self, authenticated_client, romaneo_factory):
        """Preview on PENDIENTE returns 409."""
        r = romaneo_factory()
        response = authenticated_client.get(
            f"/api/v1/acopio/romaneos/{r.pk}/merma-preview/"
        )
        assert response.status_code == 409


@pytest.mark.django_db
class TestQualityAnalysisNestedAPI:
    """Nested QA endpoints under /romaneos/{romaneo_pk}/quality-analysis/."""

    def test_create_qa_201(self, authenticated_client, romaneo_en_proceso):
        """POST creates QualityAnalysis for EN_PROCESO romaneo."""
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_en_proceso.pk}/quality-analysis/",
            {
                "humedad_pct": "15.20",
                "materias_extranas_pct": "1.80",
                "granos_danados_pct": "2.00",
                "granos_quebrados_pct": "3.00",
                "granos_ardidos_pct": "0.50",
                "cuerpos_extranos_pct": "0.10",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_get_qa_200(self, authenticated_client, romaneo_analizado):
        """GET returns the attached QualityAnalysis."""
        response = authenticated_client.get(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/quality-analysis/"
        )
        assert response.status_code == 200
        assert "humedad_pct" in response.data

    def test_patch_qa_analizado_200(self, authenticated_client, romaneo_analizado):
        """PATCH on QA allowed when romaneo is ANALIZADO."""
        response = authenticated_client.patch(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/quality-analysis/",
            {"humedad_pct": "15.50"},
            format="json",
        )
        assert response.status_code == 200

    def test_patch_qa_conforme_409(
        self,
        authenticated_client,
        romaneo_analizado,
        merma_table_factory,
        tolerance_table_factory,
        storage_unit_factory,
    ):
        """QA update blocked when romaneo is CONFORME."""
        merma_table_factory(romaneo_analizado.grain_type)
        tolerance_table_factory(romaneo_analizado.grain_type)

        # Spec-12: storage_unit must be assigned before confirmar
        unit = storage_unit_factory(branch=romaneo_analizado.branch)
        romaneo_analizado.storage_unit = unit
        romaneo_analizado.save(update_fields=["storage_unit_id"])

        # Confirm to CONFORME first
        authenticated_client.post(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/confirmar/",
            {"grado_asignado": 1},
            format="json",
        )

        response = authenticated_client.patch(
            f"/api/v1/acopio/romaneos/{romaneo_analizado.pk}/quality-analysis/",
            {"humedad_pct": "99.00"},
            format="json",
        )
        assert response.status_code == 409

    def test_create_qa_pendiente_409(self, authenticated_client, romaneo_factory):
        """Cannot create QA when romaneo is PENDIENTE."""
        r = romaneo_factory()
        response = authenticated_client.post(
            f"/api/v1/acopio/romaneos/{r.pk}/quality-analysis/",
            {
                "humedad_pct": "15.20",
                "materias_extranas_pct": "1.80",
                "granos_danados_pct": "2.00",
                "granos_quebrados_pct": "3.00",
                "granos_ardidos_pct": "0.50",
                "cuerpos_extranos_pct": "0.10",
            },
            format="json",
        )
        assert response.status_code == 409
