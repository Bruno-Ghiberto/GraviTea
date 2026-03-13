"""
Unit tests for WSAA authentication client.

Covers T024 (TRA XML generation) and T025 (CMS signing + login parsing).

T024: TRA XML structure — uniqueId=timestamp, generationTime=now-5m,
      expirationTime=now+10m, service element, XML declaration.
T025: CMS/PKCS#7 signing — valid key+cert, invalid key raises, invalid cert raises.
      Login response parsing — valid XML, missing elements, malformed XML.

Spec source: specs/invoice-backend-developement/tasks.md
"""

from __future__ import annotations

import base64
import datetime
from unittest.mock import MagicMock, patch

import pytest
from lxml import etree

from apps.facturacion.arca.exceptions import ARCAAuthError
from apps.facturacion.arca.wsaa import (
    WSAAClient,
    WSAA_WSDL_PRODUCTION,
    WSAA_WSDL_TESTING,
)


# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def wsaa_client():
    """Create a WSAAClient instance."""
    return WSAAClient()


@pytest.fixture
def sample_tra(wsaa_client):
    """Generate a sample TRA XML bytes."""
    return wsaa_client.generate_tra(service="wsfe")


# ============================================================
# T024: TRA XML Generation Tests
# ============================================================


@pytest.mark.unit
class TestGenerateTRA:
    """
    Tests for WSAAClient.generate_tra() — TRA XML structure and content.

    TRA = Login Ticket Request sent to WSAA for authentication.
    """

    def test_returns_bytes(self, wsaa_client):
        """generate_tra returns bytes (UTF-8 encoded XML)."""
        result = wsaa_client.generate_tra()
        assert isinstance(result, bytes)

    def test_valid_xml(self, wsaa_client):
        """Output is well-formed XML."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        assert root.tag == "loginTicketRequest"

    def test_xml_declaration(self, wsaa_client):
        """Output includes XML declaration with UTF-8 encoding."""
        tra_xml = wsaa_client.generate_tra()
        assert tra_xml.startswith(b"<?xml ")
        assert b"UTF-8" in tra_xml

    def test_version_attribute(self, wsaa_client):
        """Root element has version='1.0' attribute."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        assert root.get("version") == "1.0"

    def test_header_element_exists(self, wsaa_client):
        """TRA contains <header> element."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        header = root.find("header")
        assert header is not None

    def test_unique_id_is_timestamp(self, wsaa_client):
        """uniqueId is a valid integer timestamp."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        unique_id = root.find("header/uniqueId")
        assert unique_id is not None
        assert unique_id.text is not None
        value = int(unique_id.text)
        # Should be a reasonable Unix timestamp (after 2020)
        assert value > 1577836800  # 2020-01-01
        # Should be close to current time (within 60s)
        import time
        assert abs(value - int(time.time())) < 60

    def test_generation_time_backdated_5m(self, wsaa_client):
        """generationTime is approximately now minus 5 minutes."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        gen_time_el = root.find("header/generationTime")
        assert gen_time_el is not None
        assert gen_time_el.text is not None

        # Parse the datetime string
        gen_time_str = gen_time_el.text
        # Format: YYYY-MM-DDTHH:MM:SS+HHMM
        gen_time = datetime.datetime.fromisoformat(gen_time_str)

        from django.utils import timezone
        now = timezone.now()
        expected = now - datetime.timedelta(minutes=5)
        # Allow 30s tolerance for test execution time
        assert abs((gen_time - expected).total_seconds()) < 30

    def test_expiration_time_ahead_10m(self, wsaa_client):
        """expirationTime is approximately now plus 10 minutes."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        exp_time_el = root.find("header/expirationTime")
        assert exp_time_el is not None
        assert exp_time_el.text is not None

        exp_time = datetime.datetime.fromisoformat(exp_time_el.text)

        from django.utils import timezone
        now = timezone.now()
        expected = now + datetime.timedelta(minutes=10)
        assert abs((exp_time - expected).total_seconds()) < 30

    def test_time_window_15_minutes(self, wsaa_client):
        """Total window between generationTime and expirationTime is ~15 minutes."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)

        gen_time = datetime.datetime.fromisoformat(
            root.find("header/generationTime").text
        )
        exp_time = datetime.datetime.fromisoformat(
            root.find("header/expirationTime").text
        )

        window = (exp_time - gen_time).total_seconds()
        # Should be exactly 15 minutes (900 seconds)
        assert abs(window - 900) < 2

    def test_service_element_default_wsfe(self, wsaa_client):
        """Default service is 'wsfe'."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)
        service = root.find("service")
        assert service is not None
        assert service.text == "wsfe"

    def test_service_element_custom(self, wsaa_client):
        """Custom service name is set in TRA."""
        tra_xml = wsaa_client.generate_tra(service="ws_sr_padron_a5")
        root = etree.fromstring(tra_xml)
        service = root.find("service")
        assert service.text == "ws_sr_padron_a5"

    def test_xml_structure_complete(self, wsaa_client):
        """TRA has all required elements: header (uniqueId, generationTime, expirationTime), service."""
        tra_xml = wsaa_client.generate_tra()
        root = etree.fromstring(tra_xml)

        assert root.find("header/uniqueId") is not None
        assert root.find("header/generationTime") is not None
        assert root.find("header/expirationTime") is not None
        assert root.find("service") is not None

    def test_successive_calls_different_unique_id(self, wsaa_client):
        """Two calls in succession should have the same or increasing uniqueId."""
        tra1 = wsaa_client.generate_tra()
        tra2 = wsaa_client.generate_tra()

        root1 = etree.fromstring(tra1)
        root2 = etree.fromstring(tra2)

        id1 = int(root1.find("header/uniqueId").text)
        id2 = int(root2.find("header/uniqueId").text)

        assert id2 >= id1  # Monotonically non-decreasing


# ============================================================
# T025: CMS/PKCS#7 Signing Tests
# ============================================================


@pytest.mark.unit
class TestSignTRA:
    """
    Tests for WSAAClient.sign_tra() — CMS/PKCS#7 digital signing.

    Uses cryptography library to sign TRA XML with RSA private key
    and X.509 certificate.
    """

    def test_valid_signature_returns_base64(self, wsaa_client, sample_tra):
        """Valid key+cert produces base64-encoded output."""
        # Generate a real test key pair
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography import x509
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

        # Self-signed cert
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "test"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
            )
            .sign(key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)

        result = wsaa_client.sign_tra(sample_tra, key_pem, cert_pem)

        assert isinstance(result, bytes)
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_invalid_private_key_raises(self, wsaa_client, sample_tra):
        """Invalid private key PEM raises ARCAAuthError."""
        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client.sign_tra(
                sample_tra,
                b"not a valid key",
                b"not a cert",
            )
        assert exc_info.value.code == "WSAA_KEY_LOAD_ERROR"

    def test_invalid_cert_raises(self, wsaa_client, sample_tra):
        """Valid key but invalid cert PEM raises ARCAAuthError."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client.sign_tra(sample_tra, key_pem, b"not a cert")
        assert exc_info.value.code == "WSAA_CERT_LOAD_ERROR"

    def test_mismatched_key_cert_raises(self, wsaa_client, sample_tra):
        """Key that doesn't match the certificate raises ARCAAuthError."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography import x509
        from cryptography.x509.oid import NameOID

        # Generate two different key pairs
        key1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        key1_pem = key1.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

        # Cert uses key2's public key
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "test"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key2.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
            )
            .sign(key2, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)

        # Sign with key1 but cert for key2 — should fail
        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client.sign_tra(sample_tra, key1_pem, cert_pem)
        assert exc_info.value.code == "WSAA_SIGN_ERROR"


# ============================================================
# T025: Login Response Parsing Tests
# ============================================================


@pytest.mark.unit
class TestParseLoginResponse:
    """
    Tests for WSAAClient._parse_login_response() — XML response parsing.

    Validates extraction of Token and Sign from WSAA LoginCms response.
    """

    def test_valid_response(self, wsaa_client):
        """Valid WSAA response returns (token, sign) tuple."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token>SAMPLE_TOKEN_VALUE</token>
            <sign>SAMPLE_SIGN_VALUE</sign>
          </credentials>
        </loginTicketResponse>"""

        token, sign = wsaa_client._parse_login_response(xml)
        assert token == "SAMPLE_TOKEN_VALUE"
        assert sign == "SAMPLE_SIGN_VALUE"

    def test_whitespace_stripped(self, wsaa_client):
        """Token and Sign values have whitespace stripped."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token>  TOKEN_WITH_SPACES  </token>
            <sign>  SIGN_WITH_SPACES  </sign>
          </credentials>
        </loginTicketResponse>"""

        token, sign = wsaa_client._parse_login_response(xml)
        assert token == "TOKEN_WITH_SPACES"
        assert sign == "SIGN_WITH_SPACES"

    def test_missing_credentials_raises(self, wsaa_client):
        """Response without <credentials> element raises ARCAAuthError."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <error>Something went wrong</error>
        </loginTicketResponse>"""

        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client._parse_login_response(xml)
        assert exc_info.value.code == "WSAA_PARSE_ERROR"
        assert "credentials" in exc_info.value.message

    def test_missing_token_raises(self, wsaa_client):
        """Response without <token> element raises ARCAAuthError."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <sign>SIGN_VALUE</sign>
          </credentials>
        </loginTicketResponse>"""

        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client._parse_login_response(xml)
        assert exc_info.value.code == "WSAA_PARSE_ERROR"
        assert "token" in exc_info.value.message

    def test_missing_sign_raises(self, wsaa_client):
        """Response without <sign> element raises ARCAAuthError."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token>TOKEN_VALUE</token>
          </credentials>
        </loginTicketResponse>"""

        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client._parse_login_response(xml)
        assert exc_info.value.code == "WSAA_PARSE_ERROR"
        assert "sign" in exc_info.value.message

    def test_empty_token_raises(self, wsaa_client):
        """Empty <token> element raises ARCAAuthError."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token></token>
            <sign>SIGN_VALUE</sign>
          </credentials>
        </loginTicketResponse>"""

        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client._parse_login_response(xml)
        assert exc_info.value.code == "WSAA_PARSE_ERROR"

    def test_malformed_xml_raises(self, wsaa_client):
        """Malformed XML raises ARCAAuthError."""
        xml = "not valid xml at all <<<"

        with pytest.raises(ARCAAuthError) as exc_info:
            wsaa_client._parse_login_response(xml)
        assert exc_info.value.code == "WSAA_PARSE_ERROR"

    def test_nested_credentials(self, wsaa_client):
        """Token and Sign can be found in deeply nested structure."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body>
            <loginTicketResponse>
              <credentials>
                <token>DEEP_TOKEN</token>
                <sign>DEEP_SIGN</sign>
              </credentials>
            </loginTicketResponse>
          </soapenv:Body>
        </soapenv:Envelope>"""

        token, sign = wsaa_client._parse_login_response(xml)
        assert token == "DEEP_TOKEN"
        assert sign == "DEEP_SIGN"


# ============================================================
# T025: Login SOAP Call Tests (mocked)
# ============================================================


@pytest.mark.unit
class TestLogin:
    """
    Tests for WSAAClient.login() — SOAP call to WSAA LoginCms.

    All tests mock the zeep Client to avoid real network calls.
    """

    def test_login_success(self, wsaa_client):
        """Successful login returns (token, sign) tuple."""
        mock_response = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token>MOCK_TOKEN</token>
            <sign>MOCK_SIGN</sign>
          </credentials>
        </loginTicketResponse>"""

        with patch("apps.facturacion.arca.wsaa.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.service.loginCms.return_value = mock_response
            mock_client_cls.return_value = mock_instance

            token, sign = wsaa_client.login(b"c2lnbmVkX2RhdGE=", WSAA_WSDL_TESTING)

        assert token == "MOCK_TOKEN"
        assert sign == "MOCK_SIGN"

    def test_login_soap_fault_raises(self, wsaa_client):
        """SOAP fault from WSAA raises ARCAAuthError."""
        from zeep.exceptions import Fault as ZeepFault

        with patch("apps.facturacion.arca.wsaa.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.service.loginCms.side_effect = ZeepFault("cert expired")
            mock_client_cls.return_value = mock_instance

            with pytest.raises(ARCAAuthError) as exc_info:
                wsaa_client.login(b"c2lnbmVk", WSAA_WSDL_TESTING)
            assert exc_info.value.code == "WSAA_SOAP_FAULT"

    def test_login_network_error_raises(self, wsaa_client):
        """Network error raises ARCAAuthError."""
        with patch("apps.facturacion.arca.wsaa.Client") as mock_client_cls:
            mock_client_cls.side_effect = ConnectionError("connection refused")

            with pytest.raises(ARCAAuthError) as exc_info:
                wsaa_client.login(b"c2lnbmVk", WSAA_WSDL_TESTING)
            assert exc_info.value.code == "WSAA_REQUEST_ERROR"

    def test_login_passes_decoded_cms(self, wsaa_client):
        """login() decodes CMS bytes to string for SOAP call."""
        mock_response = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token>T</token>
            <sign>S</sign>
          </credentials>
        </loginTicketResponse>"""

        with patch("apps.facturacion.arca.wsaa.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.service.loginCms.return_value = mock_response
            mock_client_cls.return_value = mock_instance

            wsaa_client.login(b"c2lnbmVkX2RhdGE=", WSAA_WSDL_TESTING)

            # Verify the CMS was passed as decoded string
            call_args = mock_instance.service.loginCms.call_args
            assert call_args.kwargs.get("in0") == "c2lnbmVkX2RhdGE="

    def test_login_uses_correct_wsdl(self, wsaa_client):
        """login() creates zeep Client with the provided WSDL URL."""
        mock_response = """<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketResponse>
          <credentials>
            <token>T</token>
            <sign>S</sign>
          </credentials>
        </loginTicketResponse>"""

        with patch("apps.facturacion.arca.wsaa.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.service.loginCms.return_value = mock_response
            mock_client_cls.return_value = mock_instance

            wsaa_client.login(b"c2lnbmVk", WSAA_WSDL_PRODUCTION)

            mock_client_cls.assert_called_once_with(WSAA_WSDL_PRODUCTION)


# ============================================================
# T025: Authenticate (convenience method) Tests
# ============================================================


@pytest.mark.unit
class TestAuthenticate:
    """
    Tests for WSAAClient.authenticate() — full auth flow convenience method.
    """

    def test_authenticate_chains_flow(self, wsaa_client):
        """authenticate() chains generate_tra → sign_tra → login."""
        with (
            patch.object(wsaa_client, "generate_tra", return_value=b"<tra/>") as mock_tra,
            patch.object(wsaa_client, "sign_tra", return_value=b"c2lnbmVk") as mock_sign,
            patch.object(wsaa_client, "login", return_value=("T", "S")) as mock_login,
        ):
            token, sign = wsaa_client.authenticate(
                private_key_pem=b"key",
                cert_pem=b"cert",
                service="wsfe",
                is_production=False,
            )

        assert token == "T"
        assert sign == "S"
        mock_tra.assert_called_once_with("wsfe")
        mock_sign.assert_called_once_with(b"<tra/>", b"key", b"cert")
        mock_login.assert_called_once_with(
            b"c2lnbmVk", WSAA_WSDL_TESTING, environment="homologacion"
        )

    def test_authenticate_production_wsdl(self, wsaa_client):
        """authenticate(is_production=True) uses production WSDL."""
        with (
            patch.object(wsaa_client, "generate_tra", return_value=b"<tra/>"),
            patch.object(wsaa_client, "sign_tra", return_value=b"c2lnbmVk"),
            patch.object(wsaa_client, "login", return_value=("T", "S")) as mock_login,
        ):
            wsaa_client.authenticate(
                private_key_pem=b"key",
                cert_pem=b"cert",
                is_production=True,
            )

        mock_login.assert_called_once_with(
            b"c2lnbmVk", WSAA_WSDL_PRODUCTION, environment="production"
        )

    def test_authenticate_propagates_auth_error(self, wsaa_client):
        """ARCAAuthError from any step propagates to caller."""
        with patch.object(
            wsaa_client,
            "generate_tra",
            side_effect=ARCAAuthError("fail", "WSAA_TEST_ERROR"),
        ):
            with pytest.raises(ARCAAuthError) as exc_info:
                wsaa_client.authenticate(
                    private_key_pem=b"key",
                    cert_pem=b"cert",
                )
            assert exc_info.value.code == "WSAA_TEST_ERROR"


# ============================================================
# WSDL URL Constants Tests
# ============================================================


@pytest.mark.unit
class TestWSAAConstants:
    """Tests for WSAA WSDL URL constants."""

    def test_testing_wsdl_url(self):
        """Testing WSDL points to wsaahomo.afip.gov.ar."""
        assert "wsaahomo.afip.gov.ar" in WSAA_WSDL_TESTING
        assert "WSDL" in WSAA_WSDL_TESTING

    def test_production_wsdl_url(self):
        """Production WSDL points to wsaa.afip.gov.ar."""
        assert "wsaa.afip.gov.ar" in WSAA_WSDL_PRODUCTION
        assert "homo" not in WSAA_WSDL_PRODUCTION
        assert "WSDL" in WSAA_WSDL_PRODUCTION
