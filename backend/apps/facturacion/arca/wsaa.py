"""
WSAA (Web Service de Autenticacion y Autorizacion) client.

Handles the TRA generation, CMS/PKCS#7 signing, and LoginCms SOAP
call to obtain Token+Sign credentials for ARCA web services.

Flow:
    1. generate_tra(service) → TRA XML bytes
    2. sign_tra(tra_xml, key_pem, cert_pem) → base64 CMS signature
    3. login(signed_cms, wsdl_url) → (token, sign) tuple

Caching:
    Token+Sign pairs are cached in Redis per tenant CUIT and service.
    Cache key: arca_auth:{cuit}:{service}:{env}
    TTL: 11 hours (1h safety margin from 12h validity).
    Proactive refresh: when remaining life < 1 hour.
"""

from __future__ import annotations

import base64
import datetime
import logging

from lxml import etree
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from django.core.cache import cache as django_cache
from django.utils import timezone
from zeep import Client
from zeep.exceptions import Fault as ZeepFault

from .exceptions import ARCAAuthError
from ..metrics import record_wsaa_auth, track_soap_call

logger = logging.getLogger("facturacion.wsaa")

# WSDL URLs for WSAA LoginCms endpoint.
WSAA_WSDL_TESTING = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL"
WSAA_WSDL_PRODUCTION = "https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL"

# Token+Sign cache TTL: 11 hours (1h safety margin from WSAA's 12h validity).
CACHE_TTL_SECONDS = 11 * 60 * 60  # 39600 seconds

# Proactive refresh threshold: re-authenticate when cache entry is older
# than this value, even though the TTL hasn't expired yet.
# 11h TTL - 1h threshold = refresh when entry is >10h old.
PROACTIVE_REFRESH_AGE_SECONDS = 10 * 60 * 60  # 36000 seconds


def _cache_key(cuit: str, service: str, *, is_production: bool = False) -> str:
    """Build the Redis cache key for a tenant's WSAA token."""
    env = "prod" if is_production else "homo"
    return f"arca_auth:{cuit}:{service}:{env}"


class WSAAClient:
    """
    WSAA authentication client for ARCA.

    Generates a TRA XML, signs it with the tenant's certificate/key,
    and calls the WSAA LoginCms endpoint to obtain a Token+Sign pair.
    """

    def generate_tra(self, service: str = "wsfe") -> bytes:
        """
        Generate a TRA (LoginTicketRequest) XML document.

        The TRA requests access to a specific ARCA web service. Time
        windows use a 5-minute backdate for NTP tolerance and a
        10-minute expiration.

        Args:
            service: Target web service identifier (e.g. 'wsfe').

        Returns:
            UTF-8 encoded TRA XML bytes.
        """
        now = timezone.now()

        tra = etree.Element("loginTicketRequest", version="1.0")
        header = etree.SubElement(tra, "header")

        unique_id = etree.SubElement(header, "uniqueId")
        unique_id.text = str(int(now.timestamp()))

        gen_time = etree.SubElement(header, "generationTime")
        gen_time.text = (now - datetime.timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

        exp_time = etree.SubElement(header, "expirationTime")
        exp_time.text = (now + datetime.timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

        svc = etree.SubElement(tra, "service")
        svc.text = service

        return etree.tostring(tra, xml_declaration=True, encoding="UTF-8")

    def sign_tra(
        self,
        tra_xml: bytes,
        private_key_pem: bytes,
        cert_pem: bytes,
    ) -> bytes:
        """
        Sign TRA XML with CMS/PKCS#7 using the tenant's credentials.

        Args:
            tra_xml: TRA XML content (from generate_tra).
            private_key_pem: PEM-encoded private key bytes.
            cert_pem: PEM-encoded X.509 certificate bytes.

        Returns:
            Base64-encoded CMS/PKCS#7 signature.

        Raises:
            ARCAAuthError: If key/certificate loading or signing fails.
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem, password=None
            )
        except (ValueError, TypeError) as exc:
            raise ARCAAuthError(
                message=f"Failed to load private key: {exc}",
                code="WSAA_KEY_LOAD_ERROR",
            ) from exc

        try:
            certificate = x509.load_pem_x509_certificate(cert_pem)
        except (ValueError, TypeError) as exc:
            raise ARCAAuthError(
                message=f"Failed to load certificate: {exc}",
                code="WSAA_CERT_LOAD_ERROR",
            ) from exc

        # Validate key-certificate match before signing
        key_pub_der = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cert_pub_der = certificate.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        if key_pub_der != cert_pub_der:
            raise ARCAAuthError(
                message="Private key does not match the certificate's public key",
                code="WSAA_SIGN_ERROR",
            )

        try:
            signed = (
                pkcs7.PKCS7SignatureBuilder()
                .set_data(tra_xml)
                .add_signer(certificate, private_key, hashes.SHA256())
                .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
            )
        except Exception as exc:
            raise ARCAAuthError(
                message=f"CMS signing failed: {exc}",
                code="WSAA_SIGN_ERROR",
            ) from exc

        return base64.b64encode(signed)

    def login(
        self,
        signed_cms: bytes,
        wsdl_url: str,
        *,
        environment: str = "homologacion",
    ) -> tuple[str, str]:
        """
        Call WSAA LoginCms to obtain a Token+Sign pair.

        Args:
            signed_cms: Base64-encoded CMS signature (from sign_tra).
            wsdl_url: WSAA WSDL URL (testing or production).

        Returns:
            Tuple of (token, sign) strings.

        Raises:
            ARCAAuthError: If the SOAP call fails or the response
                cannot be parsed.
        """
        try:
            client = Client(wsdl_url)
            with track_soap_call(operation="LoginCms", environment=environment):
                response_xml = client.service.loginCms(
                    in0=signed_cms.decode("utf-8")
                )
        except ZeepFault as exc:
            logger.error("WSAA LoginCms SOAP fault: %s", exc.message)
            raise ARCAAuthError(
                message=f"WSAA LoginCms fault: {exc.message}",
                code="WSAA_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            logger.error("WSAA LoginCms request failed: %s", exc)
            raise ARCAAuthError(
                message=f"WSAA LoginCms request failed: {exc}",
                code="WSAA_REQUEST_ERROR",
            ) from exc

        return self._parse_login_response(response_xml)

    def _parse_login_response(self, response_xml: str) -> tuple[str, str]:
        """
        Parse the LoginCms XML response to extract Token and Sign.

        The response structure is:
            <loginTicketResponse>
              <credentials>
                <token>...</token>
                <sign>...</sign>
              </credentials>
            </loginTicketResponse>

        Raises:
            ARCAAuthError: If token or sign elements are missing.
        """
        try:
            root = etree.fromstring(response_xml.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            raise ARCAAuthError(
                message=f"Failed to parse WSAA response XML: {exc}",
                code="WSAA_PARSE_ERROR",
            ) from exc

        credentials = root.find(".//credentials")
        if credentials is None:
            raise ARCAAuthError(
                message="WSAA response missing <credentials> element.",
                code="WSAA_PARSE_ERROR",
            )

        token_el = credentials.find("token")
        sign_el = credentials.find("sign")

        if token_el is None or token_el.text is None:
            raise ARCAAuthError(
                message="WSAA response missing <token> element.",
                code="WSAA_PARSE_ERROR",
            )
        if sign_el is None or sign_el.text is None:
            raise ARCAAuthError(
                message="WSAA response missing <sign> element.",
                code="WSAA_PARSE_ERROR",
            )

        token = token_el.text.strip()
        sign = sign_el.text.strip()

        logger.info("WSAA authentication successful.")
        return token, sign

    def authenticate(
        self,
        private_key_pem: bytes,
        cert_pem: bytes,
        service: str = "wsfe",
        *,
        is_production: bool = False,
    ) -> tuple[str, str]:
        """
        Full WSAA authentication flow: generate TRA, sign, login.

        Convenience method that chains generate_tra → sign_tra → login.

        Args:
            private_key_pem: PEM-encoded private key bytes.
            cert_pem: PEM-encoded certificate bytes.
            service: Target ARCA web service (default: 'wsfe').
            is_production: Use production WSAA endpoint if True.

        Returns:
            Tuple of (token, sign) strings.

        Raises:
            ARCAAuthError: On any authentication failure.
        """
        wsdl_url = WSAA_WSDL_PRODUCTION if is_production else WSAA_WSDL_TESTING
        environment = "production" if is_production else "homologacion"

        logger.info(
            "Starting WSAA authentication for service=%s production=%s",
            service,
            is_production,
        )

        tra_xml = self.generate_tra(service)
        signed_cms = self.sign_tra(tra_xml, private_key_pem, cert_pem)
        try:
            token, sign = self.login(
                signed_cms, wsdl_url, environment=environment
            )
        except ARCAAuthError:
            record_wsaa_auth(result="failure", environment=environment)
            raise
        record_wsaa_auth(result="success", environment=environment)
        return token, sign

    # ------------------------------------------------------------------
    # Token+Sign caching (Redis)
    # ------------------------------------------------------------------

    @staticmethod
    def get_cached(
        cuit: str, service: str = "wsfe", *, is_production: bool = False
    ) -> tuple[str, str] | None:
        """
        Get a cached Token+Sign pair for a tenant CUIT.

        Returns:
            (token, sign) tuple if cached and not expired, else None.
        """
        data = django_cache.get(_cache_key(cuit, service, is_production=is_production))
        if data is not None:
            return data["token"], data["sign"]
        return None

    @staticmethod
    def set_cached(
        cuit: str,
        token: str,
        sign: str,
        service: str = "wsfe",
        *,
        is_production: bool = False,
    ) -> None:
        """Cache a Token+Sign pair with 11h TTL."""
        django_cache.set(
            _cache_key(cuit, service, is_production=is_production),
            {
                "token": token,
                "sign": sign,
                "cached_at": timezone.now().isoformat(),
            },
            CACHE_TTL_SECONDS,
        )

    @staticmethod
    def invalidate(
        cuit: str, service: str = "wsfe", *, is_production: bool = False
    ) -> None:
        """Force invalidation of cached token for a tenant CUIT."""
        django_cache.delete(_cache_key(cuit, service, is_production=is_production))
        logger.info("Invalidated WSAA cache for cuit=%s service=%s", cuit, service)

    @staticmethod
    def _needs_proactive_refresh(
        cuit: str, service: str = "wsfe", *, is_production: bool = False
    ) -> bool:
        """Check if the cached token is old enough to warrant proactive refresh."""
        data = django_cache.get(_cache_key(cuit, service, is_production=is_production))
        if data is None:
            return True
        cached_at_str = data.get("cached_at")
        if not cached_at_str:
            return True
        cached_at = datetime.datetime.fromisoformat(cached_at_str)
        age = (timezone.now() - cached_at).total_seconds()
        return age >= PROACTIVE_REFRESH_AGE_SECONDS

    def get_or_refresh(
        self,
        cuit: str,
        private_key_pem: bytes,
        cert_pem: bytes,
        service: str = "wsfe",
        *,
        is_production: bool = False,
    ) -> tuple[str, str]:
        """
        Get cached Token+Sign or authenticate and cache a new pair.

        Implements proactive refresh: if the cached entry has less
        than 1 hour of remaining life (i.e. older than 10 hours),
        a fresh authentication is performed even though the cache
        hasn't expired yet.

        Args:
            cuit: Tenant CUIT (11 digits, used as cache key).
            private_key_pem: PEM-encoded private key bytes.
            cert_pem: PEM-encoded certificate bytes.
            service: Target ARCA web service (default: 'wsfe').
            is_production: Use production WSAA endpoint if True.

        Returns:
            Tuple of (token, sign) strings.

        Raises:
            ARCAAuthError: On authentication failure.
        """
        if not self._needs_proactive_refresh(cuit, service, is_production=is_production):
            cached = self.get_cached(cuit, service, is_production=is_production)
            if cached is not None:
                logger.debug(
                    "Using cached WSAA token for cuit=%s service=%s",
                    cuit,
                    service,
                )
                return cached

        logger.info(
            "Refreshing WSAA token for cuit=%s service=%s", cuit, service
        )
        token, sign = self.authenticate(
            private_key_pem,
            cert_pem,
            service,
            is_production=is_production,
        )
        self.set_cached(cuit, token, sign, service, is_production=is_production)
        return token, sign
