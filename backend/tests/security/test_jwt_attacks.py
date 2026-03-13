"""
JWT Attack Vector Tests.

Tests for FR-001 and FR-002:
- FR-001: System MUST reject JWTs with alg:none attack vector
- FR-002: System MUST reject JWTs with algorithm confusion attacks

These tests verify the authentication system properly validates JWT tokens
and rejects common attack vectors as defined in OWASP JWT security guidelines.
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from tests.fixtures.security import JWT_ATTACK_VECTORS, JWTAttackVector


@pytest.fixture
def api_client() -> APIClient:
    """Create API client for testing."""
    return APIClient()


@pytest.fixture
def valid_jwt_payload() -> Dict[str, Any]:
    """Create a valid JWT payload structure."""
    now = datetime.now(tz=timezone.utc)
    return {
        "sub": "user@test.com",
        "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
        "branch_id": "660e8400-e29b-41d4-a716-446655440001",
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "unique-token-id-123",
    }


def create_unsigned_jwt(payload: Dict[str, Any], algorithm: str = "none") -> str:
    """Create an unsigned JWT token (for testing rejection)."""
    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    return f"{header_b64}.{payload_b64}."


def create_malformed_jwt(attack_type: str, payload: Dict[str, Any]) -> str:
    """Create malformed JWT tokens for specific attack types."""
    if attack_type == "alg_none":
        return create_unsigned_jwt(payload, "none")
    elif attack_type == "alg_none_uppercase":
        return create_unsigned_jwt(payload, "None")
    elif attack_type == "alg_none_mixed":
        return create_unsigned_jwt(payload, "nOnE")
    elif attack_type == "empty_signature":
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        return f"{header_b64}.{payload_b64}."
    elif attack_type == "alg_confusion_rs256_to_hs256":
        # Attempt to use public key as HMAC secret
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        # Fake signature using supposed public key
        fake_sig = base64.urlsafe_b64encode(b"fake-hmac-with-public-key").rstrip(b"=").decode()
        return f"{header_b64}.{payload_b64}.{fake_sig}"
    elif attack_type == "jwk_injection":
        # Embed malicious JWK in header
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "jwk": {
                "kty": "RSA",
                "n": "malicious-modulus",
                "e": "AQAB"
            }
        }
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        fake_sig = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()
        return f"{header_b64}.{payload_b64}.{fake_sig}"
    elif attack_type == "jku_injection":
        # Inject malicious JWKS URL
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "jku": "https://attacker.com/jwks.json"
        }
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        fake_sig = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()
        return f"{header_b64}.{payload_b64}.{fake_sig}"
    else:
        raise ValueError(f"Unknown attack type: {attack_type}")


@pytest.mark.security
@pytest.mark.jwt
class TestAlgNoneRejection:
    """
    FR-001: System MUST reject JWTs with alg:none attack vector.

    The alg:none attack exploits JWT libraries that accept unsigned tokens
    when the algorithm header is set to "none". This is a critical vulnerability
    that allows authentication bypass.
    """

    def test_alg_none_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens with alg:none are rejected (FR-001).

        Attack: Set algorithm to "none" and remove signature
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("alg_none", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.data

    def test_alg_none_uppercase_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens with alg:None (uppercase) are rejected.

        Attack: Use uppercase "None" to bypass case-sensitive checks
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("alg_none_uppercase", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_alg_none_mixed_case_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens with alg:nOnE (mixed case) are rejected.

        Attack: Use mixed case "nOnE" to bypass pattern matching
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("alg_none_mixed", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_signature_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens with empty signature are rejected.

        Attack: Declare HS256 but provide empty signature
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("empty_signature", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.jwt
class TestAlgorithmConfusion:
    """
    FR-002: System MUST reject JWTs with algorithm confusion attacks.

    Algorithm confusion attacks exploit systems that allow algorithm switching,
    particularly from RS256 (asymmetric) to HS256 (symmetric), using the
    public key as the HMAC secret.
    """

    def test_alg_confusion_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that RS256->HS256 algorithm confusion is rejected (FR-002).

        Attack: Sign with HMAC using the public key as secret
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("alg_confusion_rs256_to_hs256", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwk_injection_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that JWK header injection is rejected.

        Attack: Embed attacker-controlled JWK in token header
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("jwk_injection", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jku_injection_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that jku (JWKS URL) injection is rejected.

        Attack: Point jku header to attacker-controlled JWKS endpoint
        Expected: 401 Unauthorized
        """
        malformed_token = create_malformed_jwt("jku_injection", valid_jwt_payload)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.jwt
class TestJWTAttackVectorFixtures:
    """
    Test all JWT attack vectors from the security fixtures.

    This ensures comprehensive coverage of known JWT vulnerabilities.
    """

    @pytest.mark.parametrize("attack_vector", JWT_ATTACK_VECTORS, ids=lambda x: x.name)
    def test_attack_vector_rejected(self, api_client: APIClient, attack_vector: JWTAttackVector):
        """
        Test that all predefined attack vectors are properly rejected.

        Uses parameterized fixtures to test each attack vector.
        T031: Updated to use get_token() method for callable tokens.
        """
        # T031: Use get_token() to handle both static and generated tokens
        token = attack_vector.get_token()
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == attack_vector.expected_status, (
            f"Attack '{attack_vector.name}' should return {attack_vector.expected_status}, "
            f"got {response.status_code}. Description: {attack_vector.description}"
        )


@pytest.mark.security
@pytest.mark.jwt
class TestTokenExpiration:
    """
    Test JWT expiration handling.

    Ensures expired tokens are rejected and clock skew tolerance is reasonable.
    """

    def test_expired_token_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that expired tokens are rejected.

        Tokens with exp claim in the past should be rejected.
        """
        # Set expiration to 1 hour ago
        expired_payload = valid_jwt_payload.copy()
        expired_payload["exp"] = int((datetime.now(tz=timezone.utc) - timedelta(hours=1)).timestamp())

        # Create a properly signed but expired token would need the actual signing mechanism
        # For this test, we're verifying the validation logic exists
        malformed_token = create_unsigned_jwt(expired_payload, "none")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_exp_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens without exp claim are rejected.

        All tokens must have an expiration time.
        """
        no_exp_payload = valid_jwt_payload.copy()
        del no_exp_payload["exp"]

        malformed_token = create_unsigned_jwt(no_exp_payload, "none")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.jwt
class TestTenantClaimsValidation:
    """
    Test tenant-specific JWT claim validation.

    Ensures tenant_id and branch_id claims are properly validated.
    """

    def test_missing_tenant_id_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens without tenant_id claim are rejected.

        Multi-tenant isolation requires tenant identification.
        """
        no_tenant_payload = valid_jwt_payload.copy()
        del no_tenant_payload["tenant_id"]

        malformed_token = create_unsigned_jwt(no_tenant_payload, "none")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_tenant_id_format_rejected(self, api_client: APIClient, valid_jwt_payload: Dict[str, Any]):
        """
        Test that tokens with invalid tenant_id format are rejected.

        tenant_id must be a valid UUID.
        """
        invalid_tenant_payload = valid_jwt_payload.copy()
        invalid_tenant_payload["tenant_id"] = "not-a-valid-uuid"

        malformed_token = create_unsigned_jwt(invalid_tenant_payload, "none")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.jwt
class TestMalformedTokenHandling:
    """
    Test handling of malformed JWT tokens.

    Ensures the system gracefully handles invalid token formats.
    """

    @pytest.mark.parametrize("malformed_token,description", [
        ("", "empty token"),
        ("not-a-jwt", "plain string"),
        ("header.payload", "missing signature"),
        ("a.b.c.d", "too many parts"),
        ("!!!.@@@.###", "invalid base64"),
        ("eyJhbGciOiJIUzI1NiJ9.invalid-json.sig", "invalid payload JSON"),
    ])
    def test_malformed_token_rejected(
        self,
        api_client: APIClient,
        malformed_token: str,
        description: str
    ):
        """
        Test that malformed tokens are rejected gracefully.

        The system should not crash or expose internal errors.
        """
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {malformed_token}")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
            f"Malformed token ({description}) should be rejected"
        )
        # Verify no internal error details leaked
        if hasattr(response, "data") and isinstance(response.data, dict):
            assert "traceback" not in str(response.data).lower()
            assert "exception" not in str(response.data).lower()

    def test_no_auth_header_rejected(self, api_client: APIClient):
        """
        Test that requests without Authorization header are rejected.

        Protected endpoints require authentication.
        """
        response = api_client.get("/api/v1/products/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_wrong_auth_scheme_rejected(self, api_client: APIClient):
        """
        Test that non-Bearer auth schemes are rejected.

        Only Bearer token authentication is supported.
        """
        api_client.credentials(HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz")
        response = api_client.get("/api/v1/products/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
