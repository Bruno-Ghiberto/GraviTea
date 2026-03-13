"""
End-to-end quickstart validation for the facturacion module.

Walks through the full lifecycle documented in quickstart.md:
  1. Create ARCACredential via API.
  2. Create PuntoDeVenta via API.
  3. Issue Factura B via /comprobantes/emitir/ (mocked ARCA).
  4. Verify CAE in response.
  5. Get fiscal QR URL for the authorized comprobante.
  6. Issue Nota de Credito B referencing the Factura.
  7. Request CAEA via /caeas/solicitar/ (mocked ARCA).

All external ARCA calls are mocked; the test validates the full
Django request/response path end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status as http_status

from apps.facturacion.constants import ComprobanteStatus

# Import test constants from facturacion conftest
from tests.facturacion.conftest import SAMPLE_CERT_PEM, SAMPLE_KEY_PEM, TEST_CUIT


# ============================================================
# E2E Quickstart Smoke Test
# ============================================================

CREDENTIALS_URL = "/api/v1/facturacion/credentials/"
PUNTOS_DE_VENTA_URL = "/api/v1/facturacion/puntos-de-venta/"
COMPROBANTES_URL = "/api/v1/facturacion/comprobantes/"
EMITIR_URL = f"{COMPROBANTES_URL}emitir/"
CAEAS_URL = "/api/v1/facturacion/caeas/"
SOLICITAR_URL = f"{CAEAS_URL}solicitar/"


@pytest.mark.django_db
class TestE2EQuickstartFlow:
    """
    Validates the complete quickstart.md flow through the API layer.

    Each test method is a step in the quickstart, executed independently
    but following the documented sequence. External ARCA calls are mocked.
    """

    # ----------------------------------------------------------
    # Step 1: Create ARCACredential
    # ----------------------------------------------------------

    def test_step1_create_credential(self, authenticated_client):
        """POST /credentials/ creates an ARCACredential for the tenant."""
        payload = {
            "cuit_holder": TEST_CUIT,
            "certificate_pem": SAMPLE_CERT_PEM,
            "private_key_pem": SAMPLE_KEY_PEM,
            "is_production": False,
        }

        response = authenticated_client.post(
            CREDENTIALS_URL, payload, format="json"
        )

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Expected 201, got {response.status_code}: {response.data}"
        )
        data = response.data
        assert data["cuit_holder"] == TEST_CUIT
        assert data["is_production"] is False
        assert "id" in data
        # certificate_pem and private_key_pem should NOT be in read response
        assert "certificate_pem" not in data
        assert "private_key_pem" not in data

    # ----------------------------------------------------------
    # Step 2: Create PuntoDeVenta
    # ----------------------------------------------------------

    def test_step2_create_punto_de_venta(self, authenticated_client):
        """POST /puntos-de-venta/ creates a PuntoDeVenta for the tenant."""
        payload = {
            "numero": 1,
            "tipo": "electronic",
            "description": "Sucursal Principal",
        }

        response = authenticated_client.post(
            PUNTOS_DE_VENTA_URL, payload, format="json"
        )

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Expected 201, got {response.status_code}: {response.data}"
        )
        data = response.data
        assert data["numero"] == 1
        assert data["tipo"] == "electronic"
        assert data["is_active"] is True
        assert "id" in data

    # ----------------------------------------------------------
    # Step 3 & 4: Issue Factura B and verify CAE
    # ----------------------------------------------------------

    @patch("apps.facturacion.views.InvoiceService")
    def test_step3_issue_factura_b_and_verify_cae(
        self, MockInvoiceService, authenticated_client, punto_venta, comprobante_factory
    ):
        """
        POST /comprobantes/emitir/ issues a Factura B and returns CAE.

        Mocks InvoiceService to avoid real ARCA calls. Validates the
        full request/response path including serializer validation.
        """
        authorized = comprobante_factory(
            status="AUTORIZADO",
            cae="71234567890123",
            cae_fch_vto=date.today() + timedelta(days=10),
        )
        mock_service = MockInvoiceService.return_value
        mock_service.issue_comprobante.return_value = authorized

        payload = {
            "punto_venta": str(punto_venta.id),
            "cbte_tipo": 6,  # Factura B
            "concepto": 1,  # Productos
            "doc_tipo": 80,  # CUIT
            "doc_nro": "20345678901",
            "cbte_fch": "2026-02-10",
            "imp_total": "1210.00",
            "imp_neto": "1000.00",
            "imp_iva": "210.00",
            "imp_trib": "0.00",
            "imp_op_ex": "0.00",
            "imp_tot_conc": "0.00",
            "emitter_condicion_iva": 1,
            "receptor_condicion_iva": 5,
            "alic_iva": [
                {"iva_id": 5, "base_imp": "1000.00", "importe": "210.00"},
            ],
        }

        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Expected 201, got {response.status_code}: {response.data}"
        )
        data = response.data
        # Step 4: Verify CAE is present
        assert data["cae"] == "71234567890123"
        assert data["status"] == ComprobanteStatus.AUTORIZADO

        # Verify InvoiceService was called correctly
        mock_service.issue_comprobante.assert_called_once()
        call_kwargs = mock_service.issue_comprobante.call_args.kwargs
        assert "tenant_id" in call_kwargs
        assert "validated_data" in call_kwargs

    # ----------------------------------------------------------
    # Step 5: Get fiscal QR URL
    # ----------------------------------------------------------

    @patch("apps.facturacion.views.generate_fiscal_qr_data")
    def test_step5_get_qr_url(
        self,
        mock_qr_func,
        authenticated_client,
        authorized_comprobante,
    ):
        """
        GET /comprobantes/{id}/qr/ returns the fiscal QR URL.

        Uses an authorized_comprobante fixture (status=AUTORIZADO).
        """
        mock_qr_func.return_value = (
            "https://www.afip.gob.ar/fe/qr/?p=eyJ0ZXN0IjogdHJ1ZX0="
        )

        url = f"{COMPROBANTES_URL}{authorized_comprobante.id}/qr/"
        response = authenticated_client.get(url)

        assert response.status_code == http_status.HTTP_200_OK, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )
        assert "qr_url" in response.data
        assert response.data["qr_url"].startswith("https://www.afip.gob.ar/fe/qr/")
        mock_qr_func.assert_called_once_with(authorized_comprobante)

    # ----------------------------------------------------------
    # Step 6: Issue Nota de Credito B referencing the Factura
    # ----------------------------------------------------------

    @patch("apps.facturacion.views.InvoiceService")
    def test_step6_issue_nota_credito_b(
        self,
        MockInvoiceService,
        authenticated_client,
        authorized_comprobante,
        punto_venta,
        comprobante_factory,
    ):
        """
        POST /comprobantes/emitir/ issues a NC B referencing an existing Factura B.

        Validates CbtesAsoc type compatibility (US6): NC B (8) -> Factura B (6).
        """
        nc_authorized = comprobante_factory(
            cbte_tipo=8,  # NC B
            cbte_nro=2,
            status="AUTORIZADO",
            cae="71234567890456",
            cae_fch_vto=date.today() + timedelta(days=10),
            imp_total=Decimal("605.000"),
            imp_neto=Decimal("500.000"),
            imp_iva=Decimal("105.000"),
        )
        mock_service = MockInvoiceService.return_value
        mock_service.issue_comprobante.return_value = nc_authorized

        payload = {
            "punto_venta": str(punto_venta.id),
            "cbte_tipo": 8,  # NC B
            "concepto": 1,
            "doc_tipo": 80,
            "doc_nro": "20345678901",
            "cbte_fch": "2026-02-10",
            "imp_total": "605.00",
            "imp_neto": "500.00",
            "imp_iva": "105.00",
            "imp_trib": "0.00",
            "imp_op_ex": "0.00",
            "imp_tot_conc": "0.00",
            "emitter_condicion_iva": 1,
            "receptor_condicion_iva": 5,
            "alic_iva": [
                {"iva_id": 5, "base_imp": "500.00", "importe": "105.00"},
            ],
            "cbtes_asoc": [
                {
                    "tipo": 6,  # Factura B (same letter)
                    "pto_vta": punto_venta.numero,
                    "nro": authorized_comprobante.cbte_nro,
                },
            ],
        }

        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Expected 201, got {response.status_code}: {response.data}"
        )
        data = response.data
        assert data["cae"] == "71234567890456"
        assert data["status"] == ComprobanteStatus.AUTORIZADO

    # ----------------------------------------------------------
    # Step 7: Request CAEA (offline invoicing code)
    # ----------------------------------------------------------

    @patch("apps.facturacion.views.CAEAService")
    @patch("apps.facturacion.views.ARCAClient")
    def test_step7_solicitar_caea(
        self,
        MockARCAClient,
        MockCAEAService,
        authenticated_client,
        punto_venta,
    ):
        """
        POST /caeas/solicitar/ requests a CAEA code from ARCA.

        Mocks ARCAClient.get_auth_context and CAEAService.solicitar_caea.
        """

        @dataclass
        class MockAuthContext:
            token: str = "mock-token"
            sign: str = "mock-sign"
            cuit: str = TEST_CUIT
            is_production: bool = False

        mock_arca = MockARCAClient.return_value
        mock_arca.get_auth_context.return_value = MockAuthContext()

        @dataclass
        class MockCAEAResult:
            caea: str = "91234567890123"
            periodo: str = "202602"
            orden: int = 1
            fch_vig_desde: str = "20260201"
            fch_vig_hasta: str = "20260215"
            fch_tope_inf: str = "20260220"

        mock_caea_svc = MockCAEAService.return_value
        mock_caea_svc.solicitar_caea.return_value = MockCAEAResult()

        payload = {
            "punto_venta": str(punto_venta.id),
            "periodo": "202602",
            "orden": 1,
        }

        response = authenticated_client.post(
            SOLICITAR_URL, payload, format="json"
        )

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Expected 201, got {response.status_code}: {response.data}"
        )
        data = response.data
        assert data["caea_code"] == "91234567890123"
        assert data["periodo"] == "202602"
        assert data["orden"] == 1
        assert data["status"] == "ACTIVE"

        # Verify the auth context was fetched
        mock_arca.get_auth_context.assert_called_once()
        # Verify CAEA was requested
        mock_caea_svc.solicitar_caea.assert_called_once_with(
            pto_vta=punto_venta.numero,
            periodo="202602",
            orden=1,
        )


@pytest.mark.django_db
class TestE2EErrorPaths:
    """
    Validate error paths in the quickstart flow.

    Ensures the system returns correct error responses when
    ARCA rejects comprobantes or the service is unavailable.
    """

    @patch("apps.facturacion.views.InvoiceService")
    def test_arca_rejection_returns_422_with_observations(
        self, MockInvoiceService, authenticated_client, punto_venta
    ):
        """ARCA rejection returns 422 with type URN and observations."""
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected

        mock_service = MockInvoiceService.return_value
        mock_service.issue_comprobante.side_effect = ARCAComprobanteRejected(
            message="Comprobante rechazado por ARCA",
            code="10016",
            observations=[{"Code": "10016", "Msg": "El campo DocNro es invalido"}],
        )

        payload = {
            "punto_venta": str(punto_venta.id),
            "cbte_tipo": 6,
            "concepto": 1,
            "doc_tipo": 80,
            "doc_nro": "20345678901",
            "cbte_fch": "2026-02-10",
            "imp_total": "1210.00",
            "imp_neto": "1000.00",
            "imp_iva": "210.00",
            "imp_trib": "0.00",
            "imp_op_ex": "0.00",
            "imp_tot_conc": "0.00",
            "emitter_condicion_iva": 1,
            "receptor_condicion_iva": 5,
            "alic_iva": [
                {"iva_id": 5, "base_imp": "1000.00", "importe": "210.00"},
            ],
        }

        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.data
        assert data["type"] == "urn:gravitea:facturacion:comprobante-rejected"
        assert data["arca_code"] == "10016"
        assert "observations" in data
        assert any(
            o.get("Msg") == "El campo DocNro es invalido"
            for o in data["observations"]
        )

    @patch("apps.facturacion.views.InvoiceService")
    def test_arca_service_error_returns_502(
        self, MockInvoiceService, authenticated_client, punto_venta
    ):
        """ARCA service unavailability returns 502 with type URN."""
        from apps.facturacion.arca.exceptions import ARCARequestError

        mock_service = MockInvoiceService.return_value
        mock_service.issue_comprobante.side_effect = ARCARequestError(
            message="ARCA service unavailable",
            code="CONNECTION_TIMEOUT",
        )

        payload = {
            "punto_venta": str(punto_venta.id),
            "cbte_tipo": 6,
            "concepto": 1,
            "doc_tipo": 80,
            "doc_nro": "20345678901",
            "cbte_fch": "2026-02-10",
            "imp_total": "1210.00",
            "imp_neto": "1000.00",
            "imp_iva": "210.00",
            "imp_trib": "0.00",
            "imp_op_ex": "0.00",
            "imp_tot_conc": "0.00",
            "emitter_condicion_iva": 1,
            "receptor_condicion_iva": 5,
            "alic_iva": [
                {"iva_id": 5, "base_imp": "1000.00", "importe": "210.00"},
            ],
        }

        response = authenticated_client.post(EMITIR_URL, payload, format="json")

        assert response.status_code == http_status.HTTP_502_BAD_GATEWAY
        data = response.data
        assert data["type"] == "urn:gravitea:facturacion:arca-error"
        assert data["arca_code"] == "CONNECTION_TIMEOUT"

    def test_unauthenticated_access_blocked(self, api_client):
        """All facturacion endpoints require authentication."""
        endpoints = [
            (CREDENTIALS_URL, "get"),
            (PUNTOS_DE_VENTA_URL, "get"),
            (COMPROBANTES_URL, "get"),
            (EMITIR_URL, "post"),
            (SOLICITAR_URL, "post"),
        ]

        for url, method in endpoints:
            response = getattr(api_client, method)(url)
            assert response.status_code == http_status.HTTP_401_UNAUTHORIZED, (
                f"{method.upper()} {url} should return 401, "
                f"got {response.status_code}"
            )

    def test_tenant_isolation_across_all_resources(
        self,
        authenticated_client,
        other_tenant_comprobante,
        other_tenant_credential,
        tenant_context,
    ):
        """Resources from other tenants are not visible."""
        from apps.core.managers.tenant_bound import set_current_tenant_id

        # Restore primary tenant context (other_tenant fixtures may have cleared it)
        set_current_tenant_id(tenant_context.id)

        # Other tenant's comprobante should not appear in list
        response = authenticated_client.get(COMPROBANTES_URL)
        assert response.status_code == http_status.HTTP_200_OK
        results = response.data.get("results", [])
        other_ids = [str(other_tenant_comprobante.id)]
        visible_ids = [str(r["id"]) for r in results]
        for oid in other_ids:
            assert oid not in visible_ids, (
                f"Other tenant comprobante {oid} visible to primary tenant"
            )

        # Other tenant's credential should not appear in list
        response = authenticated_client.get(CREDENTIALS_URL)
        assert response.status_code == http_status.HTTP_200_OK
        results = response.data.get("results", [])
        visible_cred_ids = [str(r["id"]) for r in results]
        assert str(other_tenant_credential.id) not in visible_cred_ids
