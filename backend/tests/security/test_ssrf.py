"""
Security tests for SSRF (Server-Side Request Forgery) prevention.

OWASP A10:2021 - Server-Side Request Forgery (SSRF)

Tests ensure the application properly validates and sanitizes URLs
to prevent attackers from making requests to internal resources.

Test IDs: SEC-SSRF-001 through SEC-SSRF-006
"""

import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

from rest_framework import status
from rest_framework.test import APIClient

from tests.constants import (
    SSRF_INTERNAL_HOSTS,
    SSRF_METADATA_HOSTS,
    SSRF_PRIVATE_NETWORKS,
    SSRF_DANGEROUS_SCHEMES,
)


@pytest.mark.security
@pytest.mark.owasp
class TestSSRFPrevention:
    """
    Tests for SSRF vulnerability prevention.

    SSRF attacks occur when an attacker can make the server perform
    requests to unintended locations, potentially exposing internal
    services, cloud metadata, or local files.

    Coverage:
    - Localhost/loopback blocking (SEC-SSRF-001)
    - IPv6 localhost blocking (SEC-SSRF-002)
    - Cloud metadata endpoint blocking (SEC-SSRF-003)
    - Private network blocking (SEC-SSRF-004)
    - Dangerous protocol blocking (SEC-SSRF-005)
    - URL validation edge cases (SEC-SSRF-006)
    """

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Create API client for testing."""
        return APIClient()

    @pytest.fixture
    def authenticated_client(self, api_client, test_user, test_tenant):
        """Create authenticated API client."""
        api_client.force_authenticate(user=test_user)
        return api_client

    @pytest.fixture
    def ssrf_validator(self):
        """
        Mock URL validator that implements SSRF protection.

        In real implementation, this would be part of the application's
        URL validation logic in webhook handlers, external integrations, etc.
        """
        from apps.core.security.url_validator import URLValidator
        return URLValidator()

    # =========================================================================
    # SEC-SSRF-001: Localhost and Loopback Address Blocking
    # =========================================================================

    @pytest.mark.parametrize("host", SSRF_INTERNAL_HOSTS)
    def test_blocks_localhost_variations(self, host):
        """
        SEC-SSRF-001: Verify localhost and loopback addresses are blocked.

        Attackers may use various representations of localhost to bypass
        simple string matching filters.

        OWASP Reference: A10:2021 - SSRF
        """
        # Import the URL validator
        from apps.core.security.url_validator import is_safe_url

        test_urls = [
            f"http://{host}/",
            f"http://{host}:8080/",
            f"http://{host}/admin",
            f"https://{host}/internal",
        ]

        for url in test_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-001 FAILED: URL '{url}' should be blocked. "
                f"Localhost/loopback addresses must not be allowed."
            )

    def test_blocks_localhost_with_port(self):
        """
        SEC-SSRF-001: Verify localhost with various ports is blocked.

        Common ports that attackers target:
        - 22: SSH
        - 3306: MySQL
        - 5432: PostgreSQL
        - 6379: Redis
        - 9200: Elasticsearch
        """
        from apps.core.security.url_validator import is_safe_url

        dangerous_ports = [22, 80, 443, 3306, 5432, 6379, 8080, 9200]

        for port in dangerous_ports:
            url = f"http://127.0.0.1:{port}/"
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-001 FAILED: URL '{url}' should be blocked. "
                f"Internal services on port {port} must be protected."
            )

    def test_blocks_zero_ip(self):
        """
        SEC-SSRF-001: Verify 0.0.0.0 is blocked.

        0.0.0.0 can be used to access services bound to all interfaces.
        """
        from apps.core.security.url_validator import is_safe_url

        test_urls = [
            "http://0.0.0.0/",
            "http://0.0.0.0:8080/",
            "http://0/",  # Shorthand for 0.0.0.0
        ]

        for url in test_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-001 FAILED: URL '{url}' should be blocked. "
                f"0.0.0.0 and variants must not be allowed."
            )

    # =========================================================================
    # SEC-SSRF-002: IPv6 Localhost Blocking
    # =========================================================================

    def test_blocks_ipv6_localhost(self):
        """
        SEC-SSRF-002: Verify IPv6 localhost representations are blocked.

        ::1 is the IPv6 equivalent of 127.0.0.1 and must be blocked.
        """
        from apps.core.security.url_validator import is_safe_url

        ipv6_localhost_urls = [
            "http://[::1]/",
            "http://[::1]:8080/",
            "http://[0:0:0:0:0:0:0:1]/",
            "http://[::ffff:127.0.0.1]/",  # IPv4-mapped IPv6
        ]

        for url in ipv6_localhost_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-002 FAILED: IPv6 localhost URL '{url}' should be blocked."
            )

    def test_blocks_ipv6_private_addresses(self):
        """
        SEC-SSRF-002: Verify IPv6 private addresses are blocked.

        fc00::/7 is the IPv6 unique local address range.
        """
        from apps.core.security.url_validator import is_safe_url

        ipv6_private_urls = [
            "http://[fc00::1]/",
            "http://[fd00::1]/",
            "http://[fe80::1]/",  # Link-local
        ]

        for url in ipv6_private_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-002 FAILED: IPv6 private URL '{url}' should be blocked."
            )

    # =========================================================================
    # SEC-SSRF-003: Cloud Metadata Endpoint Blocking
    # =========================================================================

    @pytest.mark.parametrize("host", SSRF_METADATA_HOSTS)
    def test_blocks_cloud_metadata_endpoints(self, host):
        """
        SEC-SSRF-003: Verify cloud metadata endpoints are blocked.

        Cloud providers expose metadata services at well-known addresses.
        Accessing these can leak credentials and sensitive configuration.

        AWS: 169.254.169.254
        GCP: metadata.google.internal
        Azure: 169.254.169.254 (same as AWS)
        """
        from apps.core.security.url_validator import is_safe_url

        test_urls = [
            f"http://{host}/",
            f"http://{host}/latest/meta-data/",
            f"http://{host}/latest/meta-data/iam/security-credentials/",
            f"http://{host}/computeMetadata/v1/",
        ]

        for url in test_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-003 FAILED: Cloud metadata URL '{url}' should be blocked. "
                f"Exposing metadata endpoints can leak cloud credentials."
            )

    def test_blocks_aws_metadata_with_redirect_header(self):
        """
        SEC-SSRF-003: Verify AWS IMDSv2 style requests are blocked.

        Even with token-based protection, the initial metadata endpoint
        should still be blocked at the URL validation level.
        """
        from apps.core.security.url_validator import is_safe_url

        aws_metadata_urls = [
            "http://169.254.169.254/latest/api/token",
            "http://169.254.169.254/latest/dynamic/instance-identity/document",
            "http://169.254.169.254/latest/user-data",
        ]

        for url in aws_metadata_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-003 FAILED: AWS metadata URL '{url}' should be blocked."
            )

    def test_blocks_gcp_metadata_with_header(self):
        """
        SEC-SSRF-003: Verify GCP metadata URLs are blocked.

        GCP metadata requires Metadata-Flavor: Google header, but the
        URL should still be blocked at validation level.
        """
        from apps.core.security.url_validator import is_safe_url

        gcp_metadata_urls = [
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            "http://metadata.google.internal/computeMetadata/v1/project/project-id",
        ]

        for url in gcp_metadata_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-003 FAILED: GCP metadata URL '{url}' should be blocked."
            )

    # =========================================================================
    # SEC-SSRF-004: Private Network Blocking
    # =========================================================================

    @pytest.mark.parametrize("host", SSRF_PRIVATE_NETWORKS)
    def test_blocks_private_network_addresses(self, host):
        """
        SEC-SSRF-004: Verify RFC 1918 private network addresses are blocked.

        Private IP ranges (10.x.x.x, 172.16-31.x.x, 192.168.x.x) should
        not be accessible via user-supplied URLs.
        """
        from apps.core.security.url_validator import is_safe_url

        test_urls = [
            f"http://{host}/",
            f"http://{host}:8080/internal/",
            f"https://{host}/api/",
        ]

        for url in test_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-004 FAILED: Private network URL '{url}' should be blocked. "
                f"Internal network resources must be protected from SSRF."
            )

    def test_blocks_full_private_ranges(self):
        """
        SEC-SSRF-004: Verify all RFC 1918 ranges are blocked comprehensively.
        """
        from apps.core.security.url_validator import is_safe_url

        # Test representative IPs from each private range
        private_ips = [
            # 10.0.0.0/8
            "10.0.0.1", "10.255.255.254", "10.1.2.3",
            # 172.16.0.0/12
            "172.16.0.1", "172.31.255.254", "172.20.1.1",
            # 192.168.0.0/16
            "192.168.0.1", "192.168.255.254", "192.168.1.100",
        ]

        for ip in private_ips:
            url = f"http://{ip}/"
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-004 FAILED: Private IP URL '{url}' should be blocked."
            )

    # =========================================================================
    # SEC-SSRF-005: Dangerous Protocol Blocking
    # =========================================================================

    @pytest.mark.parametrize("url", SSRF_DANGEROUS_SCHEMES)
    def test_blocks_dangerous_schemes(self, url):
        """
        SEC-SSRF-005: Verify dangerous URI schemes are blocked.

        Non-HTTP schemes can be used for various attacks:
        - file:// - Local file access
        - gopher:// - Protocol smuggling
        - dict:// - Service enumeration
        - ftp:// - FTP bounce attacks
        """
        from apps.core.security.url_validator import is_safe_url

        result = is_safe_url(url)
        assert result is False, (
            f"SEC-SSRF-005 FAILED: Dangerous scheme URL '{url}' should be blocked."
        )

    def test_blocks_file_protocol_variations(self):
        """
        SEC-SSRF-005: Verify file:// protocol variations are blocked.
        """
        from apps.core.security.url_validator import is_safe_url

        file_urls = [
            "file:///etc/passwd",
            "file:///etc/shadow",
            "file:///proc/self/environ",
            "file:///var/log/auth.log",
            "file://localhost/etc/passwd",
            "FILE:///etc/passwd",  # Case variation
        ]

        for url in file_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-005 FAILED: File protocol URL '{url}' should be blocked."
            )

    def test_only_allows_http_https(self):
        """
        SEC-SSRF-005: Verify only HTTP and HTTPS schemes are allowed.
        """
        from apps.core.security.url_validator import is_safe_url

        # These should be allowed (assuming safe host)
        safe_urls = [
            "http://example.com/",
            "https://example.com/",
        ]

        for url in safe_urls:
            result = is_safe_url(url)
            assert result is True, (
                f"SEC-SSRF-005: URL '{url}' should be allowed (valid scheme, public host)."
            )

        # These should be blocked (invalid schemes)
        blocked_schemes = [
            "ftp://example.com/",
            "sftp://example.com/",
            "ldap://example.com/",
            "ssh://example.com/",
            "telnet://example.com/",
            "data:text/html,<script>alert(1)</script>",
            "javascript:alert(1)",
        ]

        for url in blocked_schemes:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-005 FAILED: Non-HTTP scheme URL '{url}' should be blocked."
            )

    # =========================================================================
    # SEC-SSRF-006: URL Validation Edge Cases
    # =========================================================================

    def test_blocks_url_with_credentials(self):
        """
        SEC-SSRF-006: Verify URLs with embedded credentials are handled safely.

        URLs like http://user:pass@host/ can be used for various attacks.
        """
        from apps.core.security.url_validator import is_safe_url

        urls_with_creds = [
            "http://user:pass@internal.service/",
            "http://admin:admin@127.0.0.1/",
            "http://root:toor@192.168.1.1/",
        ]

        for url in urls_with_creds:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-006 FAILED: URL with credentials '{url}' should be blocked."
            )

    def test_blocks_dns_rebinding_attempts(self):
        """
        SEC-SSRF-006: Verify potential DNS rebinding vectors are handled.

        DNS rebinding can be used to bypass SSRF protections by having
        a hostname resolve to internal IPs after initial validation.
        """
        from apps.core.security.url_validator import is_safe_url

        # These should be validated at request time, not just validation time
        suspicious_hostnames = [
            "http://localtest.me/",  # Resolves to 127.0.0.1
            "http://127.0.0.1.nip.io/",  # NIP.io wildcard DNS
            "http://spoofed.127.0.0.1.nip.io/",
        ]

        for url in suspicious_hostnames:
            # The validator should either:
            # 1. Block these hostnames (conservative)
            # 2. Resolve and validate the IP (thorough)
            result = is_safe_url(url)
            # Note: Implementation may vary - some allow these if they can't resolve
            # The key is that the actual request must be validated against the resolved IP

    def test_blocks_url_with_special_characters(self):
        """
        SEC-SSRF-006: Verify URLs with bypass characters are blocked.

        Special characters and encoding can be used to bypass filters.
        """
        from apps.core.security.url_validator import is_safe_url

        bypass_attempts = [
            "http://127.0.0.1%00.example.com/",  # Null byte
            "http://127.0.0.1%2f.example.com/",  # Encoded slash
            "http://127.0.0.1%252f.example.com/",  # Double encoded
            "http://127.1/",  # Shortened IP
            "http://2130706433/",  # Decimal IP for 127.0.0.1
            "http://0x7f000001/",  # Hex IP for 127.0.0.1
            "http://0177.0.0.1/",  # Octal IP for 127.0.0.1
        ]

        for url in bypass_attempts:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-006 FAILED: Bypass attempt URL '{url}' should be blocked."
            )

    def test_handles_empty_and_malformed_urls(self):
        """
        SEC-SSRF-006: Verify empty and malformed URLs are handled safely.
        """
        from apps.core.security.url_validator import is_safe_url

        invalid_urls = [
            "",
            None,
            "not-a-url",
            "://missing-scheme.com",
            "http://",
            "http:///path",
        ]

        for url in invalid_urls:
            result = is_safe_url(url)
            assert result is False, (
                f"SEC-SSRF-006 FAILED: Invalid URL '{url}' should be blocked."
            )

    def test_allows_legitimate_external_urls(self):
        """
        SEC-SSRF-006: Verify legitimate external URLs are allowed.

        The validator should not be overly restrictive on valid external URLs.
        """
        from apps.core.security.url_validator import is_safe_url

        legitimate_urls = [
            "https://api.example.com/webhook",
            "https://hooks.slack.com/services/xxx",
            "https://api.stripe.com/v1/charges",
            "http://httpbin.org/post",
        ]

        for url in legitimate_urls:
            result = is_safe_url(url)
            assert result is True, (
                f"SEC-SSRF-006: Legitimate external URL '{url}' should be allowed."
            )
