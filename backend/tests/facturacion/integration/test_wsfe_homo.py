"""
WSFEv1 homologation integration test.

Covers T058: Full FECompUltimoAutorizado + FECAESolicitar + FECompConsultar
flow against ARCA's homologation environment (wswhomo.afip.gov.ar).

Requires real ARCA homologation certificate, key, and a valid CUIT.
Set environment variables to enable:
    ARCA_TEST_CERT_PATH=/path/to/cert.pem
    ARCA_TEST_KEY_PATH=/path/to/key.pem
    ARCA_TEST_CUIT=20123456789

Skip reason: These tests hit the real ARCA homologation server.
Run explicitly with: pytest -m integration tests/facturacion/integration/

Spec source: specs/invoice-backend-developement/tasks.md (Phase 10)
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from apps.facturacion.arca.exceptions import (
    ARCAComprobanteRejected,
    ARCARequestError,
)
from apps.facturacion.arca.wsaa import WSAA_WSDL_TESTING, WSAAClient
from apps.facturacion.arca.wsfe import CAEResult, WSFEv1Client

# ---------------------------------------------------------------------------
# Environment-based credential loading
# ---------------------------------------------------------------------------

CERT_PATH = os.environ.get("ARCA_TEST_CERT_PATH", "")
KEY_PATH = os.environ.get("ARCA_TEST_KEY_PATH", "")
CUIT = os.environ.get("ARCA_TEST_CUIT", "")

_has_credentials = bool(CERT_PATH and KEY_PATH and CUIT)

skip_no_credentials = pytest.mark.skipif(
    not _has_credentials,
    reason=(
        "ARCA homologation credentials not configured. "
        "Set ARCA_TEST_CERT_PATH, ARCA_TEST_KEY_PATH, and "
        "ARCA_TEST_CUIT env vars."
    ),
)


def _load_credentials() -> tuple[bytes, bytes]:
    """Load PEM certificate and key from env-configured paths."""
    cert_pem = Path(CERT_PATH).read_bytes()
    key_pem = Path(KEY_PATH).read_bytes()
    return key_pem, cert_pem


def _authenticate_wsaa() -> tuple[str, str]:
    """Obtain a fresh Token+Sign via WSAA homologation."""
    key_pem, cert_pem = _load_credentials()
    client = WSAAClient()
    return client.authenticate(
        private_key_pem=key_pem,
        cert_pem=cert_pem,
        service="wsfe",
        is_production=False,
    )


# ============================================================
# T058: WSFEv1 Homologation Integration Tests
# ============================================================


@pytest.mark.integration
@skip_no_credentials
class TestWSFEv1Homologation:
    """
    Full WSFEv1 SOAP operations against ARCA homologation.

    These tests hit the real wswhomo.afip.gov.ar endpoint.
    They exercise FECompUltimoAutorizado, FECAESolicitar, and
    FECompConsultar in sequence.
    """

    @pytest.fixture(autouse=True)
    def setup_wsfe_client(self):
        """Authenticate via WSAA and create WSFEv1Client for each test."""
        token, sign = _authenticate_wsaa()
        self.client = WSFEv1Client(
            token=token,
            sign=sign,
            cuit=CUIT,
            is_production=False,
        )
        self.pto_vta = 1  # Homologation default punto de venta
        self.cbte_tipo = 6  # Factura B (simplest for testing)

    # ----------------------------------------------------------
    # Step 1: FECompUltimoAutorizado
    # ----------------------------------------------------------

    def test_get_ultimo_comprobante_returns_integer(self):
        """FECompUltimoAutorizado returns an integer >= 0."""
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )
        assert isinstance(ultimo, int)
        assert ultimo >= 0

    def test_get_ultimo_comprobante_factura_a(self):
        """FECompUltimoAutorizado works for Factura A (type 1)."""
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=1
        )
        assert isinstance(ultimo, int)
        assert ultimo >= 0

    def test_get_ultimo_comprobante_various_types(self):
        """FECompUltimoAutorizado works across cbte_tipo values."""
        for cbte_tipo in (1, 6, 11):  # Factura A, B, C
            ultimo = self.client.get_ultimo_comprobante(
                pto_vta=self.pto_vta, cbte_tipo=cbte_tipo
            )
            assert isinstance(ultimo, int)

    # ----------------------------------------------------------
    # Step 2: FECAESolicitar — Full CAE Request
    # ----------------------------------------------------------

    def test_solicitar_cae_factura_b(self):
        """
        Full FECAESolicitar for Factura B against homologation.

        Sequence:
        1. Get ultimo comprobante number
        2. Build request data with next number
        3. Request CAE
        4. Verify CAEResult has valid CAE
        """
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )
        next_nro = ultimo + 1

        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 1,  # Productos
            "doc_tipo": 99,  # Sin identificar (for Consumidor Final)
            "doc_nro": 0,
            "cbte_nro": next_nro,
            "cbte_fch": date.today().strftime("%Y%m%d"),
            "imp_total": 121.0,
            "imp_neto": 100.0,
            "imp_iva": 21.0,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "alic_iva": [
                {"iva_id": 5, "base_imp": 100.0, "importe": 21.0},
            ],
        }

        result = self.client.solicitar_cae(data)

        assert isinstance(result, CAEResult)
        assert result.resultado in ("A", "O")
        assert result.cae is not None
        assert len(result.cae) == 14
        assert result.cae_fch_vto is not None
        assert result.cbte_nro == next_nro

    def test_solicitar_cae_returns_14_digit_cae(self):
        """CAE code from ARCA is exactly 14 digits."""
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )

        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 1,
            "doc_tipo": 99,
            "doc_nro": 0,
            "cbte_nro": ultimo + 1,
            "cbte_fch": date.today().strftime("%Y%m%d"),
            "imp_total": 50.0,
            "imp_neto": 41.32,
            "imp_iva": 8.68,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "alic_iva": [
                {"iva_id": 5, "base_imp": 41.32, "importe": 8.68},
            ],
        }

        result = self.client.solicitar_cae(data)
        assert result.cae is not None
        assert result.cae.isdigit()
        assert len(result.cae) == 14

    def test_solicitar_cae_fch_vto_format(self):
        """CAE expiration date is in YYYYMMDD format."""
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )

        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 1,
            "doc_tipo": 99,
            "doc_nro": 0,
            "cbte_nro": ultimo + 1,
            "cbte_fch": date.today().strftime("%Y%m%d"),
            "imp_total": 10.0,
            "imp_neto": 8.26,
            "imp_iva": 1.74,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "alic_iva": [
                {"iva_id": 5, "base_imp": 8.26, "importe": 1.74},
            ],
        }

        result = self.client.solicitar_cae(data)
        assert result.cae_fch_vto is not None
        assert len(result.cae_fch_vto) == 8
        assert result.cae_fch_vto.isdigit()

    # ----------------------------------------------------------
    # Step 3: FECompConsultar — Recovery Query
    # ----------------------------------------------------------

    def test_consultar_existing_comprobante(self):
        """
        FECompConsultar retrieves a previously authorized comprobante.

        Issues a CAE first, then queries it back.
        """
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )
        next_nro = ultimo + 1

        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 1,
            "doc_tipo": 99,
            "doc_nro": 0,
            "cbte_nro": next_nro,
            "cbte_fch": date.today().strftime("%Y%m%d"),
            "imp_total": 25.0,
            "imp_neto": 20.66,
            "imp_iva": 4.34,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "alic_iva": [
                {"iva_id": 5, "base_imp": 20.66, "importe": 4.34},
            ],
        }

        cae_result = self.client.solicitar_cae(data)

        # Now query it back
        consulta = self.client.consultar_comprobante(
            pto_vta=self.pto_vta,
            cbte_tipo=self.cbte_tipo,
            cbte_nro=next_nro,
        )

        assert consulta is not None
        assert consulta["cbte_nro"] == next_nro
        assert consulta["cae"] == cae_result.cae

    def test_consultar_nonexistent_comprobante(self):
        """FECompConsultar returns None for a non-existent comprobante number."""
        result = self.client.consultar_comprobante(
            pto_vta=self.pto_vta,
            cbte_tipo=self.cbte_tipo,
            cbte_nro=99999999,
        )
        assert result is None

    # ----------------------------------------------------------
    # Step 4: Error Scenarios
    # ----------------------------------------------------------

    def test_duplicate_cbte_nro_raises_rejected(self):
        """
        Submitting a duplicate CbteNro raises ARCAComprobanteRejected.

        ARCA enforces sequential numbering; re-using an existing
        number should be rejected.
        """
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )

        if ultimo == 0:
            pytest.skip("No existing comprobantes to duplicate")

        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 1,
            "doc_tipo": 99,
            "doc_nro": 0,
            "cbte_nro": ultimo,  # Duplicate — already exists
            "cbte_fch": date.today().strftime("%Y%m%d"),
            "imp_total": 10.0,
            "imp_neto": 8.26,
            "imp_iva": 1.74,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "alic_iva": [
                {"iva_id": 5, "base_imp": 8.26, "importe": 1.74},
            ],
        }

        with pytest.raises((ARCAComprobanteRejected, ARCARequestError)):
            self.client.solicitar_cae(data)

    def test_invalid_amounts_raises_error(self):
        """
        FECAESolicitar with mismatched amounts raises rejection.

        imp_total must equal imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc.
        """
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )

        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 1,
            "doc_tipo": 99,
            "doc_nro": 0,
            "cbte_nro": ultimo + 1,
            "cbte_fch": date.today().strftime("%Y%m%d"),
            "imp_total": 999.99,  # Intentionally wrong
            "imp_neto": 100.0,
            "imp_iva": 21.0,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "alic_iva": [
                {"iva_id": 5, "base_imp": 100.0, "importe": 21.0},
            ],
        }

        with pytest.raises((ARCAComprobanteRejected, ARCARequestError)):
            self.client.solicitar_cae(data)

    # ----------------------------------------------------------
    # Step 5: Servicios Concept (dates required)
    # ----------------------------------------------------------

    def test_servicios_concept_requires_dates(self):
        """
        Concepto 2 (Servicios) includes service date fields.

        This verifies ARCA accepts the request when
        fch_serv_desde, fch_serv_hasta, fch_vto_pago are provided.
        """
        ultimo = self.client.get_ultimo_comprobante(
            pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo
        )

        today = date.today()
        data = {
            "punto_venta": self.pto_vta,
            "cbte_tipo": self.cbte_tipo,
            "concepto": 2,  # Servicios
            "doc_tipo": 99,
            "doc_nro": 0,
            "cbte_nro": ultimo + 1,
            "cbte_fch": today.strftime("%Y%m%d"),
            "imp_total": 242.0,
            "imp_neto": 200.0,
            "imp_iva": 42.0,
            "imp_trib": 0.0,
            "imp_op_ex": 0.0,
            "imp_tot_conc": 0.0,
            "mon_id": "PES",
            "mon_cotiz": 1.0,
            "fch_serv_desde": (today - timedelta(days=30)).strftime("%Y%m%d"),
            "fch_serv_hasta": today.strftime("%Y%m%d"),
            "fch_vto_pago": (today + timedelta(days=15)).strftime("%Y%m%d"),
            "alic_iva": [
                {"iva_id": 5, "base_imp": 200.0, "importe": 42.0},
            ],
        }

        result = self.client.solicitar_cae(data)
        assert result.resultado in ("A", "O")
        assert result.cae is not None
