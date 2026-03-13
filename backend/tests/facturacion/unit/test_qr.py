"""
Unit tests for fiscal QR code generation.

Covers T042: generate_fiscal_qr_data — JSON payload structure (13 fields),
base64url encoding (no padding), URL prefix, error cases for non-authorized
and missing CAE comprobantes, round-trip decode verification.

Spec source: specs/invoice-backend-developement/tasks.md (Phase 8)
"""

from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.facturacion.qr import QR_BASE_URL, generate_fiscal_qr_data
from tests.facturacion.conftest import TEST_CUIT


# ============================================================
# T042: Fiscal QR — JSON Payload Structure
# ============================================================


@pytest.mark.django_db
class TestQRPayloadStructure:
    """Verify the QR JSON payload contains all 13 required fields."""

    def _decode_payload(self, url: str) -> dict:
        """Extract and decode the base64url JSON payload from a QR URL."""
        prefix = f"{QR_BASE_URL}?p="
        assert url.startswith(prefix)
        encoded = url[len(prefix):]
        decoded = base64.urlsafe_b64decode(encoded + "==")  # pad for decoding
        return json.loads(decoded)

    def test_payload_has_all_13_fields(self, authorized_comprobante):
        """QR payload must contain exactly the 13 ARCA-required fields."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)

        required_fields = {
            "ver", "fecha", "cuit", "ptoVta", "tipoCmp", "nroCmp",
            "importe", "moneda", "ctz", "tipoDocRec", "nroDocRec",
            "tipoCodAut", "codAut",
        }
        assert set(payload.keys()) == required_fields

    def test_ver_is_always_1(self, authorized_comprobante):
        """ver field is always 1 per ARCA spec."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["ver"] == 1

    def test_fecha_format_yyyy_mm_dd(self, authorized_comprobante):
        """fecha uses YYYY-MM-DD format."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        # Verify format matches ISO date
        parsed = date.fromisoformat(payload["fecha"])
        assert parsed == authorized_comprobante.cbte_fch

    def test_cuit_is_integer_no_hyphens(self, authorized_comprobante):
        """cuit is an integer (no hyphens or dashes)."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert isinstance(payload["cuit"], int)
        assert payload["cuit"] == int(TEST_CUIT)

    def test_pto_vta_from_punto_venta_numero(self, authorized_comprobante):
        """ptoVta comes from punto_venta.numero (FK relationship)."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["ptoVta"] == authorized_comprobante.punto_venta.numero

    def test_tipo_cmp_matches_cbte_tipo(self, authorized_comprobante):
        """tipoCmp matches the comprobante's cbte_tipo."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["tipoCmp"] == authorized_comprobante.cbte_tipo

    def test_nro_cmp_matches_cbte_nro(self, authorized_comprobante):
        """nroCmp matches the comprobante's cbte_nro."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["nroCmp"] == authorized_comprobante.cbte_nro

    def test_importe_is_float(self, authorized_comprobante):
        """importe is a float representation of imp_total."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert isinstance(payload["importe"], float)
        assert payload["importe"] == float(authorized_comprobante.imp_total)

    def test_moneda_matches_mon_id(self, authorized_comprobante):
        """moneda matches the comprobante's mon_id."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["moneda"] == authorized_comprobante.mon_id

    def test_ctz_is_float(self, authorized_comprobante):
        """ctz is a float representation of mon_cotiz."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert isinstance(payload["ctz"], float)
        assert payload["ctz"] == float(authorized_comprobante.mon_cotiz)

    def test_tipo_doc_rec_matches_doc_tipo(self, authorized_comprobante):
        """tipoDocRec maps to doc_tipo."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["tipoDocRec"] == authorized_comprobante.doc_tipo

    def test_nro_doc_rec_is_integer(self, authorized_comprobante):
        """nroDocRec is an integer from doc_nro."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert isinstance(payload["nroDocRec"], int)
        assert payload["nroDocRec"] == int(authorized_comprobante.doc_nro)

    def test_tipo_cod_aut_is_e(self, authorized_comprobante):
        """tipoCodAut is always 'E' (CAE)."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert payload["tipoCodAut"] == "E"

    def test_cod_aut_is_cae_as_integer(self, authorized_comprobante):
        """codAut is the CAE as an integer."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        payload = self._decode_payload(url)
        assert isinstance(payload["codAut"], int)
        assert payload["codAut"] == int(authorized_comprobante.cae)


# ============================================================
# T042: Fiscal QR — Encoding & URL Format
# ============================================================


@pytest.mark.django_db
class TestQREncoding:
    """Verify base64url encoding and URL structure."""

    def test_url_starts_with_arca_prefix(self, authorized_comprobante):
        """URL starts with the official ARCA QR prefix."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        assert url.startswith(f"{QR_BASE_URL}?p=")

    def test_base64url_no_padding_characters(self, authorized_comprobante):
        """Base64url output must not contain '=' padding characters."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        encoded_part = url.split("?p=")[1]
        assert "=" not in encoded_part

    def test_base64url_no_plus_or_slash(self, authorized_comprobante):
        """Base64url uses '-' and '_' instead of '+' and '/'."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        encoded_part = url.split("?p=")[1]
        assert "+" not in encoded_part
        assert "/" not in encoded_part

    def test_compact_json_no_spaces(self, authorized_comprobante):
        """JSON uses compact separators (no spaces after : or ,)."""
        url = generate_fiscal_qr_data(authorized_comprobante)
        encoded_part = url.split("?p=")[1]
        decoded = base64.urlsafe_b64decode(encoded_part + "==")
        raw_json = decoded.decode()
        # Compact JSON has no spaces after separators
        assert ": " not in raw_json
        assert ", " not in raw_json

    def test_round_trip_decode(self, authorized_comprobante):
        """Full round-trip: generate URL → extract payload → decode → verify all fields."""
        url = generate_fiscal_qr_data(authorized_comprobante)

        # Extract encoded payload
        encoded = url.split("?p=")[1]

        # Decode base64url
        decoded = base64.urlsafe_b64decode(encoded + "==")
        payload = json.loads(decoded)

        # Verify critical fields round-trip correctly
        assert payload["ver"] == 1
        assert payload["cuit"] == int(authorized_comprobante.emitter_cuit)
        assert payload["codAut"] == int(authorized_comprobante.cae)
        assert payload["tipoCodAut"] == "E"
        assert payload["ptoVta"] == authorized_comprobante.punto_venta.numero


# ============================================================
# T042: Fiscal QR — OBSERVADO Comprobante Support
# ============================================================


@pytest.mark.django_db
class TestQRObservado:
    """Verify QR generation works for OBSERVADO comprobantes."""

    def test_observado_comprobante_generates_qr(self, observed_comprobante):
        """OBSERVADO comprobantes (with CAE + warnings) can generate QR."""
        url = generate_fiscal_qr_data(observed_comprobante)
        assert url.startswith(f"{QR_BASE_URL}?p=")

    def test_observado_cae_in_payload(self, observed_comprobante):
        """OBSERVADO comprobante's CAE appears in the QR payload."""
        url = generate_fiscal_qr_data(observed_comprobante)
        encoded = url.split("?p=")[1]
        decoded = base64.urlsafe_b64decode(encoded + "==")
        payload = json.loads(decoded)
        assert payload["codAut"] == int(observed_comprobante.cae)


# ============================================================
# T042: Fiscal QR — Error Cases
# ============================================================


@pytest.mark.django_db
class TestQRErrorCases:
    """Verify correct errors for invalid comprobante states."""

    def test_draft_comprobante_raises_value_error(self, draft_comprobante):
        """DRAFT comprobante cannot generate QR (no CAE yet)."""
        with pytest.raises(ValueError, match="status"):
            generate_fiscal_qr_data(draft_comprobante)

    def test_rechazado_comprobante_raises_value_error(self, rejected_comprobante):
        """RECHAZADO comprobante cannot generate QR."""
        with pytest.raises(ValueError, match="status"):
            generate_fiscal_qr_data(rejected_comprobante)

    def test_validando_comprobante_raises_value_error(self, comprobante_factory):
        """VALIDANDO comprobante cannot generate QR."""
        cbte = comprobante_factory(status="VALIDANDO")
        with pytest.raises(ValueError, match="status"):
            generate_fiscal_qr_data(cbte)

    def test_autorizado_without_cae_raises_value_error(self, comprobante_factory):
        """AUTORIZADO comprobante with no CAE raises ValueError."""
        cbte = comprobante_factory(status="AUTORIZADO", cae=None)
        with pytest.raises(ValueError, match="no CAE"):
            generate_fiscal_qr_data(cbte)

    def test_autorizado_with_empty_cae_raises_value_error(self, comprobante_factory):
        """AUTORIZADO comprobante with empty CAE string raises ValueError."""
        cbte = comprobante_factory(status="AUTORIZADO", cae="")
        with pytest.raises(ValueError, match="no CAE"):
            generate_fiscal_qr_data(cbte)
