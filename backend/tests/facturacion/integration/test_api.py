"""
Integration tests for Comprobante API endpoints.

Tests the ComprobanteViewSet: emitir action (success + validation + ARCA errors),
list with cursor pagination and filtering, retrieve by ID, and QR endpoint.

Covers: US2, FR-007, FR-008, FR-009, FR-010, US6 (via serializer validation).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)
from apps.facturacion.arca.exceptions import (
    ARCAAuthError,
    ARCAComprobanteRejected,
    ARCARequestError,
)

# Base URL for comprobantes
COMPROBANTES_URL = "/api/v1/facturacion/comprobantes/"
EMITIR_URL = f"{COMPROBANTES_URL}emitir/"


def _error_fields(response_data: dict) -> set[str]:
    """Extract field names from RFC 9457 Problem Details errors array."""
    return {e["field"] for e in response_data.get("errors", [])}


def _build_emitir_payload(punto_venta_id: str, **overrides) -> dict:
    """Build a valid Factura B emitir payload with optional overrides."""
    payload = {
        "punto_venta": str(punto_venta_id),
        "cbte_tipo": 6,  # Factura B
        "concepto": 1,  # Productos
        "doc_tipo": 80,  # CUIT
        "doc_nro": "20345678901",
        "cbte_fch": str(date.today()),
        "imp_total": "1210.000",
        "imp_neto": "1000.000",
        "imp_iva": "210.000",
        "imp_trib": "0.000",
        "imp_op_ex": "0.000",
        "imp_tot_conc": "0.000",
        "mon_id": "PES",
        "mon_cotiz": "1.000000",
        "emitter_condicion_iva": 1,  # RI
        "receptor_condicion_iva": 5,  # Consumidor Final
        "alic_iva": [
            {"iva_id": 5, "base_imp": "1000.000", "importe": "210.000"},
        ],
        "tributos": [],
        "cbtes_asoc": [],
    }
    payload.update(overrides)
    return payload


# ============================================================
# Emitir Endpoint Tests
# ============================================================


@pytest.mark.django_db
class TestComprobanteEmitir:
    """Test POST /api/v1/facturacion/comprobantes/emitir/."""

    @patch("apps.facturacion.views.InvoiceService")
    def test_emitir_success_returns_201(
        self,
        mock_svc_cls,
        authenticated_client,
        punto_venta,
        comprobante_factory,
    ):
        """Successful emission returns 201 with authorized comprobante data."""
        # Create a comprobante that the mocked service will "return"
        authorized = comprobante_factory(
            status="AUTORIZADO",
            cae="12345678901234",
            cae_fch_vto=date.today() + timedelta(days=10),
        )
        mock_svc_cls.return_value.issue_comprobante.return_value = authorized

        payload = _build_emitir_payload(punto_venta.id)
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "AUTORIZADO"
        assert data["cae"] == "12345678901234"
        assert data["cbte_tipo"] == 6
        assert data["punto_venta_numero"] == punto_venta.numero

        # Verify service was called with correct args
        mock_svc_cls.return_value.issue_comprobante.assert_called_once()

    @patch("apps.facturacion.views.InvoiceService")
    def test_emitir_arca_rejected_returns_422(
        self,
        mock_svc_cls,
        authenticated_client,
        punto_venta,
    ):
        """ARCA rejection returns 422 with structured error response."""
        mock_svc_cls.return_value.issue_comprobante.side_effect = (
            ARCAComprobanteRejected(
                message="Error en importes",
                code="10016",
                observations=[
                    {"Code": "10016", "Msg": "El campo ImpTotal no coincide"}
                ],
            )
        )

        payload = _build_emitir_payload(punto_venta.id)
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 422
        data = response.json()
        assert data["type"] == "urn:gravitea:facturacion:comprobante-rejected"
        assert data["status"] == 422
        assert data["arca_code"] == "10016"
        assert "observations" in data
        assert len(data["observations"]) == 1

    @patch("apps.facturacion.views.InvoiceService")
    def test_emitir_arca_request_error_returns_502(
        self,
        mock_svc_cls,
        authenticated_client,
        punto_venta,
    ):
        """ARCA SOAP failure returns 502 with error details."""
        mock_svc_cls.return_value.issue_comprobante.side_effect = (
            ARCARequestError(message="SOAP timeout", code="CONN_ERR")
        )

        payload = _build_emitir_payload(punto_venta.id)
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 502
        data = response.json()
        assert data["type"] == "urn:gravitea:facturacion:arca-error"
        assert data["status"] == 502

    @patch("apps.facturacion.views.InvoiceService")
    def test_emitir_arca_auth_error_returns_502(
        self,
        mock_svc_cls,
        authenticated_client,
        punto_venta,
    ):
        """WSAA auth failure returns 502."""
        mock_svc_cls.return_value.issue_comprobante.side_effect = ARCAAuthError(
            message="Certificate expired", code="AUTH_ERR"
        )

        payload = _build_emitir_payload(punto_venta.id)
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 502
        data = response.json()
        assert data["type"] == "urn:gravitea:facturacion:arca-error"

    def test_emitir_missing_required_fields_returns_400(
        self,
        authenticated_client,
    ):
        """Missing required fields returns 400 validation error."""
        response = authenticated_client.post(EMITIR_URL, {}, format="json")

        assert response.status_code == 400
        data = response.json()
        fields = _error_fields(data)
        # Required fields should be in the errors array
        for field in ("punto_venta", "cbte_tipo", "concepto", "doc_tipo", "doc_nro"):
            assert field in fields, f"Expected '{field}' in validation errors"

    def test_emitir_amount_equation_mismatch_returns_400(
        self,
        authenticated_client,
        punto_venta,
    ):
        """FR-007: Amount equation mismatch returns 400."""
        payload = _build_emitir_payload(
            punto_venta.id,
            imp_total="999.000",  # Wrong: 1000 + 210 = 1210, not 999
            imp_neto="1000.000",
            imp_iva="210.000",
        )
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 400
        data = response.json()
        fields = _error_fields(data)
        assert "imp_total" in fields or "non_field_errors" in fields

    def test_emitir_iva_required_for_type_a_returns_400(
        self,
        authenticated_client,
        punto_venta,
    ):
        """FR-008: Type A invoice without IVA breakdown returns 400."""
        payload = _build_emitir_payload(
            punto_venta.id,
            cbte_tipo=1,  # Factura A
            alic_iva=[],  # Missing — mandatory for A
            emitter_condicion_iva=1,
            receptor_condicion_iva=1,
        )
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 400
        data = response.json()
        fields = _error_fields(data)
        assert "alic_iva" in fields or "non_field_errors" in fields

    def test_emitir_service_dates_required_for_concepto_2_returns_400(
        self,
        authenticated_client,
        punto_venta,
    ):
        """FR-009: Service concepto without dates returns 400."""
        payload = _build_emitir_payload(
            punto_venta.id,
            concepto=2,  # Servicios
            # Dates missing
        )
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 400
        data = response.json()
        fields = _error_fields(data)
        assert "fch_serv_desde" in fields or "non_field_errors" in fields

    def test_emitir_invalid_punto_venta_returns_400(
        self,
        authenticated_client,
    ):
        """Non-existent punto de venta returns 400."""
        import uuid

        payload = _build_emitir_payload(uuid.uuid4())
        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == 400
        data = response.json()
        fields = _error_fields(data)
        assert "punto_venta" in fields

    def test_emitir_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        from rest_framework.test import APIClient

        client = APIClient()
        response = client.post(EMITIR_URL, {}, format="json")

        assert response.status_code == 401


# ============================================================
# List Endpoint Tests
# ============================================================


@pytest.mark.django_db
class TestComprobanteList:
    """Test GET /api/v1/facturacion/comprobantes/."""

    def test_list_returns_comprobantes(
        self,
        authenticated_client,
        comprobante_factory,
    ):
        """List endpoint returns comprobantes for current tenant."""
        comprobante_factory()
        comprobante_factory()
        comprobante_factory()

        response = authenticated_client.get(COMPROBANTES_URL)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 3

    def test_list_cursor_pagination(
        self,
        authenticated_client,
        comprobante_factory,
    ):
        """Cursor pagination returns next/previous links."""
        # Create enough comprobantes to trigger pagination with page_size=10
        for _ in range(25):
            comprobante_factory()

        response = authenticated_client.get(
            COMPROBANTES_URL, {"page_size": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "next" in data
        # First page should have a next link (25 items > page_size=10)
        assert data["next"] is not None

        # Follow next link
        next_response = authenticated_client.get(data["next"])
        assert next_response.status_code == 200
        next_data = next_response.json()
        assert "results" in next_data
        assert "previous" in next_data
        assert next_data["previous"] is not None

    def test_list_filter_by_status(
        self,
        authenticated_client,
        authorized_comprobante,
        draft_comprobante,
        rejected_comprobante,
    ):
        """Status filter returns only matching comprobantes."""
        response = authenticated_client.get(
            COMPROBANTES_URL, {"status": "AUTORIZADO"}
        )

        assert response.status_code == 200
        data = response.json()
        results = data["results"]
        assert len(results) == 1
        assert results[0]["status"] == "AUTORIZADO"

    def test_list_filter_by_cbte_tipo(
        self,
        authenticated_client,
        comprobante_factory,
    ):
        """cbte_tipo filter returns only matching type."""
        comprobante_factory(cbte_tipo=1)  # Factura A
        comprobante_factory(cbte_tipo=6)  # Factura B
        comprobante_factory(cbte_tipo=6)  # Factura B

        response = authenticated_client.get(COMPROBANTES_URL, {"cbte_tipo": "6"})

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 2
        assert all(r["cbte_tipo"] == 6 for r in results)

    def test_list_filter_by_punto_venta(
        self,
        authenticated_client,
        punto_venta,
        punto_venta_factory,
        comprobante_factory,
    ):
        """punto_venta filter returns only comprobantes for that PtoVta."""
        other_pv = punto_venta_factory(numero=5)
        from apps.facturacion.models import Comprobante

        # Default comprobante_factory uses the main punto_venta
        comprobante_factory()  # PtoVta 1
        comprobante_factory()  # PtoVta 1
        # Create one with different punto_venta directly
        Comprobante.objects.create(
            tenant=punto_venta.tenant,
            punto_venta=other_pv,
            cbte_tipo=6,
            cbte_nro=1,
            concepto=1,
            doc_tipo=80,
            doc_nro="20111111112",
            cbte_fch=date.today(),
            imp_total=Decimal("100.000"),
            imp_neto=Decimal("100.000"),
            imp_iva=Decimal("0.000"),
            imp_trib=Decimal("0.000"),
            imp_op_ex=Decimal("0.000"),
            imp_tot_conc=Decimal("0.000"),
            mon_id="PES",
            mon_cotiz=Decimal("1.000000"),
            emitter_cuit="20123456789",
            emitter_condicion_iva=1,
            receptor_condicion_iva=5,
            status="DRAFT",
        )

        response = authenticated_client.get(
            COMPROBANTES_URL, {"punto_venta": str(punto_venta.id)}
        )

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 2
        assert all(
            r["punto_venta"] == str(punto_venta.id) for r in results
        )

    def test_list_filter_by_fecha_range(
        self,
        authenticated_client,
        comprobante_factory,
    ):
        """fecha_from/fecha_to filters restrict by cbte_fch."""
        today = date.today()
        comprobante_factory(cbte_fch=today - timedelta(days=30))
        comprobante_factory(cbte_fch=today)
        comprobante_factory(cbte_fch=today + timedelta(days=5))

        response = authenticated_client.get(
            COMPROBANTES_URL,
            {
                "fecha_from": str(today - timedelta(days=1)),
                "fecha_to": str(today + timedelta(days=1)),
            },
        )

        assert response.status_code == 200
        results = response.json()["results"]
        # Only the "today" comprobante should match
        assert len(results) == 1

    def test_list_tenant_isolation(
        self,
        authenticated_client,
        comprobante_factory,
        other_tenant_comprobante,
        tenant_context,
    ):
        """Comprobantes from other tenants are not visible."""
        # Re-set tenant context after other_tenant_comprobante cleared it
        set_current_tenant_id(tenant_context.id)

        comprobante_factory()  # Our tenant

        response = authenticated_client.get(COMPROBANTES_URL)

        assert response.status_code == 200
        results = response.json()["results"]
        # Should only see our comprobante, not the other tenant's
        assert len(results) == 1

    def test_list_empty_returns_empty_results(
        self,
        authenticated_client,
        tenant_context,
    ):
        """Empty list returns 200 with empty results array."""
        response = authenticated_client.get(COMPROBANTES_URL)

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []


# ============================================================
# Retrieve Endpoint Tests
# ============================================================


@pytest.mark.django_db
class TestComprobanteRetrieve:
    """Test GET /api/v1/facturacion/comprobantes/{id}/."""

    def test_retrieve_returns_full_comprobante(
        self,
        authenticated_client,
        authorized_comprobante,
    ):
        """Retrieve returns comprobante with all nested data."""
        url = f"{COMPROBANTES_URL}{authorized_comprobante.id}/"
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(authorized_comprobante.id)
        assert data["status"] == "AUTORIZADO"
        assert data["cae"] == "12345678901234"
        assert data["cbte_tipo"] == 6
        # Nested arrays should be present (even if empty)
        assert "aliciva_set" in data
        assert "tributo_set" in data
        assert "cbteasoc_set" in data
        assert "punto_venta_numero" in data

    def test_retrieve_with_iva_breakdown(
        self,
        authenticated_client,
        factura_a_with_iva,
    ):
        """Retrieve includes nested AlicIva entries."""
        url = f"{COMPROBANTES_URL}{factura_a_with_iva.id}/"
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["aliciva_set"]) == 1
        iva_entry = data["aliciva_set"][0]
        assert iva_entry["iva_id"] == 5

    def test_retrieve_nonexistent_returns_404(
        self,
        authenticated_client,
    ):
        """Non-existent comprobante returns 404."""
        import uuid

        url = f"{COMPROBANTES_URL}{uuid.uuid4()}/"
        response = authenticated_client.get(url)

        assert response.status_code == 404

    def test_retrieve_other_tenant_returns_404(
        self,
        authenticated_client,
        other_tenant_comprobante,
        tenant_context,
    ):
        """Comprobante from another tenant returns 404 (tenant isolation)."""
        set_current_tenant_id(tenant_context.id)

        url = f"{COMPROBANTES_URL}{other_tenant_comprobante.id}/"
        response = authenticated_client.get(url)

        assert response.status_code == 404


# ============================================================
# QR Endpoint Tests
# ============================================================


@pytest.mark.django_db
class TestComprobanteQR:
    """Test GET /api/v1/facturacion/comprobantes/{id}/qr/."""

    @patch("apps.facturacion.views.generate_fiscal_qr_data")
    def test_qr_authorized_returns_url(
        self,
        mock_qr,
        authenticated_client,
        authorized_comprobante,
    ):
        """Authorized comprobante returns QR URL."""
        mock_qr.return_value = (
            "https://www.afip.gob.ar/fe/qr/?p=eyJ2ZXIiOjF9"
        )

        url = f"{COMPROBANTES_URL}{authorized_comprobante.id}/qr/"
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "qr_url" in data
        assert data["qr_url"].startswith("https://www.afip.gob.ar/fe/qr/")
        mock_qr.assert_called_once_with(authorized_comprobante)

    @patch("apps.facturacion.views.generate_fiscal_qr_data")
    def test_qr_draft_returns_400(
        self,
        mock_qr,
        authenticated_client,
        draft_comprobante,
    ):
        """Draft comprobante returns 400 (QR unavailable)."""
        mock_qr.side_effect = ValueError(
            "QR only available for AUTORIZADO or OBSERVADO comprobantes."
        )

        url = f"{COMPROBANTES_URL}{draft_comprobante.id}/qr/"
        response = authenticated_client.get(url)

        assert response.status_code == 400
        data = response.json()
        assert data["type"] == "urn:gravitea:facturacion:qr-unavailable"

    @patch("apps.facturacion.views.generate_fiscal_qr_data")
    def test_qr_observed_returns_url(
        self,
        mock_qr,
        authenticated_client,
        observed_comprobante,
    ):
        """Observed comprobante also returns QR URL (has CAE)."""
        mock_qr.return_value = (
            "https://www.afip.gob.ar/fe/qr/?p=eyJ2ZXIiOjJ9"
        )

        url = f"{COMPROBANTES_URL}{observed_comprobante.id}/qr/"
        response = authenticated_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "qr_url" in data

    def test_qr_nonexistent_returns_404(
        self,
        authenticated_client,
    ):
        """Non-existent comprobante returns 404."""
        import uuid

        url = f"{COMPROBANTES_URL}{uuid.uuid4()}/qr/"
        response = authenticated_client.get(url)

        assert response.status_code == 404
