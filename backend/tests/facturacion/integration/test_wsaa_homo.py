"""
WSAA homologation integration test.

Covers T057: Full TRA → CMS → LoginCms flow against ARCA's
homologation environment (wsaahomo.afip.gov.ar).

Requires real ARCA homologation certificate and key.
Set environment variables to enable:
    ARCA_TEST_CERT_PATH=/path/to/cert.pem
    ARCA_TEST_KEY_PATH=/path/to/key.pem

Skip reason: These tests hit the real ARCA homologation server.
Run explicitly with: pytest -m integration tests/facturacion/integration/

Spec source: specs/invoice-backend-developement/tasks.md (Phase 10)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from lxml import etree

from apps.facturacion.arca.exceptions import ARCAAuthError
from apps.facturacion.arca.wsaa import (
    WSAA_WSDL_TESTING,
    WSAAClient,
)

# ---------------------------------------------------------------------------
# Environment-based credential loading
# ---------------------------------------------------------------------------

CERT_PATH = os.environ.get("ARCA_TEST_CERT_PATH", "")
KEY_PATH = os.environ.get("ARCA_TEST_KEY_PATH", "")

_has_credentials = bool(CERT_PATH and KEY_PATH)

skip_no_credentials = pytest.mark.skipif(
    not _has_credentials,
    reason=(
        "ARCA homologation credentials not configured. "
        "Set ARCA_TEST_CERT_PATH and ARCA_TEST_KEY_PATH env vars."
    ),
)


def _load_credentials() -> tuple[bytes, bytes]:
    """Load PEM certificate and key from env-configured paths."""
    cert_pem = Path(CERT_PATH).read_bytes()
    key_pem = Path(KEY_PATH).read_bytes()
    return key_pem, cert_pem


# ============================================================
# T057: WSAA Homologation Integration Tests
# ============================================================


@pytest.mark.integration
@skip_no_credentials
class TestWSAAHomologation:
    """
    Full WSAA authentication flow against ARCA homologation.

    These tests hit the real wsaahomo.afip.gov.ar endpoint.
    They verify the complete TRA → CMS → LoginCms pipeline
    produces valid Token+Sign credentials.
    """

    @pytest.fixture(autouse=True)
    def setup_client_and_creds(self):
        """Load credentials and create WSAAClient for each test."""
        self.client = WSAAClient()
        self.key_pem, self.cert_pem = _load_credentials()

    # ----------------------------------------------------------
    # Step 1: TRA Generation
    # ----------------------------------------------------------

    def test_generate_tra_produces_valid_xml(self):
        """generate_tra returns well-formed XML with expected structure."""
        tra_xml = self.client.generate_tra(service="wsfe")

        assert isinstance(tra_xml, bytes)
        root = etree.fromstring(tra_xml)
        assert root.tag == "loginTicketRequest"

        header = root.find("header")
        assert header is not None
        assert header.find("uniqueId") is not None
        assert header.find("generationTime") is not None
        assert header.find("expirationTime") is not None

        service = root.find("service")
        assert service is not None
        assert service.text == "wsfe"

    # ----------------------------------------------------------
    # Step 2: CMS Signing
    # ----------------------------------------------------------

    def test_sign_tra_with_real_credentials(self):
        """sign_tra produces base64-encoded CMS with real cert/key."""
        tra_xml = self.client.generate_tra(service="wsfe")
        signed = self.client.sign_tra(tra_xml, self.key_pem, self.cert_pem)

        assert isinstance(signed, bytes)
        # Base64-encoded CMS should be decodable
        import base64

        decoded = base64.b64decode(signed)
        assert len(decoded) > 0

    # ----------------------------------------------------------
    # Step 3: LoginCms against homologation
    # ----------------------------------------------------------

    def test_login_returns_token_and_sign(self):
        """
        Full TRA→CMS→LoginCms against wsaahomo.afip.gov.ar.

        Verifies that ARCA returns a valid Token+Sign pair.
        """
        tra_xml = self.client.generate_tra(service="wsfe")
        signed_cms = self.client.sign_tra(tra_xml, self.key_pem, self.cert_pem)
        token, sign = self.client.login(signed_cms, WSAA_WSDL_TESTING)

        assert isinstance(token, str)
        assert isinstance(sign, str)
        assert len(token) > 0
        assert len(sign) > 0

    def test_token_is_not_empty_whitespace(self):
        """Token should contain meaningful content, not just whitespace."""
        tra_xml = self.client.generate_tra(service="wsfe")
        signed_cms = self.client.sign_tra(tra_xml, self.key_pem, self.cert_pem)
        token, sign = self.client.login(signed_cms, WSAA_WSDL_TESTING)

        assert token.strip() == token
        assert sign.strip() == sign

    # ----------------------------------------------------------
    # Step 4: Full authenticate convenience method
    # ----------------------------------------------------------

    def test_authenticate_full_flow(self):
        """
        authenticate() chains TRA→CMS→Login in one call.

        This is the primary integration test — exercises the
        complete WSAA authentication pipeline.
        """
        token, sign = self.client.authenticate(
            private_key_pem=self.key_pem,
            cert_pem=self.cert_pem,
            service="wsfe",
            is_production=False,
        )

        assert isinstance(token, str)
        assert isinstance(sign, str)
        assert len(token) > 100  # Real tokens are long XML-like strings
        assert len(sign) > 10

    def test_authenticate_different_service(self):
        """authenticate() works for services other than wsfe (e.g. ws_sr_padron_a13)."""
        token, sign = self.client.authenticate(
            private_key_pem=self.key_pem,
            cert_pem=self.cert_pem,
            service="ws_sr_padron_a13",
            is_production=False,
        )

        assert isinstance(token, str)
        assert len(token) > 0

    # ----------------------------------------------------------
    # Error scenarios
    # ----------------------------------------------------------

    def test_invalid_certificate_raises_auth_error(self):
        """Login with corrupt certificate raises ARCAAuthError."""
        with pytest.raises(ARCAAuthError) as exc_info:
            self.client.authenticate(
                private_key_pem=self.key_pem,
                cert_pem=b"-----BEGIN CERTIFICATE-----\nINVALID\n-----END CERTIFICATE-----\n",
                service="wsfe",
                is_production=False,
            )
        assert exc_info.value.code in (
            "WSAA_CERT_LOAD_ERROR",
            "WSAA_SIGN_ERROR",
        )

    def test_invalid_key_raises_auth_error(self):
        """Login with corrupt key raises ARCAAuthError."""
        with pytest.raises(ARCAAuthError) as exc_info:
            self.client.authenticate(
                private_key_pem=b"-----BEGIN PRIVATE KEY-----\nINVALID\n-----END PRIVATE KEY-----\n",
                cert_pem=self.cert_pem,
                service="wsfe",
                is_production=False,
            )
        assert exc_info.value.code in (
            "WSAA_KEY_LOAD_ERROR",
            "WSAA_SIGN_ERROR",
        )

    # ----------------------------------------------------------
    # Cache integration (get_or_refresh)
    # ----------------------------------------------------------

    @pytest.mark.django_db
    def test_get_or_refresh_populates_cache(self):
        """
        get_or_refresh authenticates and caches Token+Sign on first call.
        Second call uses cache without re-authenticating.
        """
        cuit = "20123456789"
        service = "wsfe"

        # First call — authenticates against ARCA
        token1, sign1 = self.client.get_or_refresh(
            cuit=cuit,
            private_key_pem=self.key_pem,
            cert_pem=self.cert_pem,
            service=service,
            is_production=False,
        )
        assert len(token1) > 0

        # Second call — should use cache
        cached = self.client.get_cached(cuit, service)
        assert cached is not None
        token2, sign2 = cached
        assert token2 == token1
        assert sign2 == sign1

        # Cleanup
        self.client.invalidate(cuit, service)
