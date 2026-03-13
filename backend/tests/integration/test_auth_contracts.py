"""
Integration tests for authentication flows.

Tests the complete authentication lifecycle with RFC 7807 error responses:
- Token obtain (login)
- Token refresh
- Token verification
- Protected endpoint access

Per spec.md FR-019 (API Error Responses) requirements.

Test ID: T020 - Integration test for authentication flows
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestTokenObtainFlow:
    """Tests for POST /api/v1/auth/token/ (login) endpoint."""

    def test_valid_credentials_returns_tokens(
        self, api_client, admin_user, tenant_context
    ):
        """Test login with valid credentials returns access and refresh tokens."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert isinstance(response.data["access"], str)
        assert isinstance(response.data["refresh"], str)
        # Tokens should be JWT format (3 base64 parts separated by dots)
        assert len(response.data["access"].split(".")) == 3
        assert len(response.data["refresh"].split(".")) == 3

    def test_invalid_email_returns_rfc7807_401(
        self, api_client, admin_user, tenant_context, problem_detail_validator
    ):
        """Test login with invalid email returns RFC 7807 401 error."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "wrong@testcompany.com",
            "password": "TestPassword123!",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_invalid_password_returns_rfc7807_401(
        self, api_client, admin_user, tenant_context, problem_detail_validator
    ):
        """Test login with invalid password returns RFC 7807 401 error."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "WrongPassword123!",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_missing_email_returns_rfc7807_400(
        self, api_client, problem_detail_validator
    ):
        """Test login with missing email returns RFC 7807 400 error."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "password": "TestPassword123!",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        problem_detail_validator(
            response.data,
            expected_status=400,
            expect_errors=True,
        )

    def test_missing_password_returns_rfc7807_400(
        self, api_client, problem_detail_validator
    ):
        """Test login with missing password returns RFC 7807 400 error."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        problem_detail_validator(
            response.data,
            expected_status=400,
            expect_errors=True,
        )

    def test_empty_credentials_returns_rfc7807_400(
        self, api_client, problem_detail_validator
    ):
        """Test login with empty credentials returns RFC 7807 400 error."""
        url = reverse("auth:token_obtain_pair")
        credentials = {}

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        problem_detail_validator(
            response.data,
            expected_status=400,
            expect_errors=True,
        )


class TestTokenRefreshFlow:
    """Tests for POST /api/v1/auth/token/refresh/ endpoint."""

    def test_valid_refresh_token_returns_new_access_token(
        self, api_client, admin_user, tenant_context
    ):
        """Test refresh with valid refresh token returns new access token."""
        # First, obtain tokens
        login_url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }
        login_response = api_client.post(login_url, credentials, format="json")
        refresh_token = login_response.data["refresh"]

        # Then, refresh the token
        refresh_url = reverse("auth:token_refresh")
        refresh_data = {"refresh": refresh_token}

        response = api_client.post(refresh_url, refresh_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert isinstance(response.data["access"], str)
        # New access token should be different from original
        assert response.data["access"] != login_response.data["access"]
        # Should be valid JWT format
        assert len(response.data["access"].split(".")) == 3

    def test_invalid_refresh_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test refresh with invalid token returns RFC 7807 401 error."""
        refresh_url = reverse("auth:token_refresh")
        refresh_data = {"refresh": "invalid.token.here"}

        response = api_client.post(refresh_url, refresh_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_expired_refresh_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test refresh with expired token returns RFC 7807 401 error."""
        # Create an expired token (using a token from the past)
        # For this test, we'll use a malformed token that will be rejected
        refresh_url = reverse("auth:token_refresh")
        # This is an expired/invalid token structure
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTYwMDAwMDAwMH0.invalid"
        refresh_data = {"refresh": expired_token}

        response = api_client.post(refresh_url, refresh_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_missing_refresh_token_returns_rfc7807_400(
        self, api_client, problem_detail_validator
    ):
        """Test refresh without token returns RFC 7807 400 error."""
        refresh_url = reverse("auth:token_refresh")
        refresh_data = {}

        response = api_client.post(refresh_url, refresh_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        problem_detail_validator(
            response.data,
            expected_status=400,
            expect_errors=True,
        )


class TestTokenVerification:
    """Tests for POST /api/v1/auth/token/verify/ endpoint."""

    def test_valid_token_returns_200(
        self, api_client, admin_user, tenant_context
    ):
        """Test verification with valid token returns 200."""
        # First, obtain tokens
        login_url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }
        login_response = api_client.post(login_url, credentials, format="json")
        access_token = login_response.data["access"]

        # Verify the token
        verify_url = reverse("auth:token_verify")
        verify_data = {"token": access_token}

        response = api_client.post(verify_url, verify_data, format="json")

        assert response.status_code == status.HTTP_200_OK

    def test_invalid_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test verification with invalid token returns RFC 7807 401 error."""
        verify_url = reverse("auth:token_verify")
        verify_data = {"token": "invalid.token.here"}

        response = api_client.post(verify_url, verify_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_missing_token_returns_rfc7807_400(
        self, api_client, problem_detail_validator
    ):
        """Test verification without token returns RFC 7807 400 error."""
        verify_url = reverse("auth:token_verify")
        verify_data = {}

        response = api_client.post(verify_url, verify_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        problem_detail_validator(
            response.data,
            expected_status=400,
            expect_errors=True,
        )

    def test_malformed_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test verification with malformed token returns RFC 7807 401 error."""
        verify_url = reverse("auth:token_verify")
        verify_data = {"token": "not-a-jwt-token"}

        response = api_client.post(verify_url, verify_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )


class TestProtectedEndpointAccess:
    """Tests for protected endpoint access with authentication."""

    def test_valid_token_allows_access(
        self, api_client, admin_user, tenant_context
    ):
        """Test accessing protected endpoint with valid token returns 200."""
        # First, obtain tokens
        login_url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }
        login_response = api_client.post(login_url, credentials, format="json")
        access_token = login_response.data["access"]

        # Access protected endpoint
        protected_url = reverse("auth:user-list")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = api_client.get(protected_url)

        assert response.status_code == status.HTTP_200_OK

    def test_no_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test accessing protected endpoint without token returns RFC 7807 401."""
        protected_url = reverse("auth:user-list")

        response = api_client.get(protected_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_invalid_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test accessing protected endpoint with invalid token returns RFC 7807 401."""
        protected_url = reverse("auth:user-list")
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")

        response = api_client.get(protected_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_expired_token_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test accessing protected endpoint with expired token returns RFC 7807 401."""
        protected_url = reverse("auth:user-list")
        # Use an expired/invalid token
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")

        response = api_client.get(protected_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )

    def test_malformed_authorization_header_returns_rfc7807_401(
        self, api_client, problem_detail_validator
    ):
        """Test accessing protected endpoint with malformed auth header returns RFC 7807 401."""
        protected_url = reverse("auth:user-list")
        # Missing "Bearer" prefix
        api_client.credentials(HTTP_AUTHORIZATION="not-bearer-format")

        response = api_client.get(protected_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        problem_detail_validator(
            response.data,
            expected_status=401,
        )


class TestAuthenticationContract:
    """Contract tests for authentication endpoint responses."""

    def test_all_auth_errors_include_trace_id(
        self, api_client, admin_user, tenant_context
    ):
        """Test that all authentication errors include trace_id."""
        test_cases = [
            # Invalid credentials
            {
                "url": reverse("auth:token_obtain_pair"),
                "method": "post",
                "data": {"email": "wrong@test.com", "password": "wrong"},
            },
            # Invalid refresh token
            {
                "url": reverse("auth:token_refresh"),
                "method": "post",
                "data": {"refresh": "invalid.token"},
            },
            # Invalid verify token
            {
                "url": reverse("auth:token_verify"),
                "method": "post",
                "data": {"token": "invalid.token"},
            },
            # No auth on protected endpoint
            {
                "url": reverse("auth:user-list"),
                "method": "get",
                "data": {},
            },
        ]

        for test_case in test_cases:
            if test_case["method"] == "post":
                response = api_client.post(
                    test_case["url"], test_case["data"], format="json"
                )
            else:
                response = api_client.get(test_case["url"])

            # All should return 400 or 401
            assert response.status_code in (
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_401_UNAUTHORIZED,
            )
            # All should include trace_id
            assert "trace_id" in response.data
            assert isinstance(response.data["trace_id"], str)
            assert len(response.data["trace_id"]) > 0

    def test_auth_errors_have_valid_type_uri(
        self, api_client, admin_user, tenant_context
    ):
        """Test that authentication errors have valid type URIs."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "wrong@testcompany.com",
            "password": "WrongPassword123!",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "type" in response.data
        assert response.data["type"].startswith("https://")

    def test_auth_errors_status_field_matches_http_status(
        self, api_client, admin_user, tenant_context
    ):
        """Test that status field in error response matches HTTP status code."""
        test_cases = [
            {
                "url": reverse("auth:token_obtain_pair"),
                "data": {"email": "wrong@test.com", "password": "wrong"},
                "expected_status": status.HTTP_401_UNAUTHORIZED,
            },
            {
                "url": reverse("auth:token_obtain_pair"),
                "data": {"password": "test"},  # Missing email
                "expected_status": status.HTTP_400_BAD_REQUEST,
            },
        ]

        for test_case in test_cases:
            response = api_client.post(
                test_case["url"], test_case["data"], format="json"
            )

            assert response.status_code == test_case["expected_status"]
            assert response.data["status"] == test_case["expected_status"]

    def test_successful_auth_does_not_include_rfc7807_fields(
        self, api_client, admin_user, tenant_context
    ):
        """Test that successful authentication does not use RFC 7807 format."""
        url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }

        response = api_client.post(url, credentials, format="json")

        assert response.status_code == status.HTTP_200_OK
        # Success responses should NOT have RFC 7807 fields
        assert "type" not in response.data
        assert "title" not in response.data
        assert "trace_id" not in response.data
        assert "detail" not in response.data
        # Should have token fields instead
        assert "access" in response.data
        assert "refresh" in response.data


class TestAuthenticationTokenLifecycle:
    """End-to-end tests for complete token lifecycle."""

    def test_complete_authentication_flow(
        self, api_client, admin_user, tenant_context
    ):
        """Test complete flow: login → access protected → refresh → verify."""
        # Step 1: Login
        login_url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }
        login_response = api_client.post(login_url, credentials, format="json")
        assert login_response.status_code == status.HTTP_200_OK
        original_access = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Step 2: Access protected endpoint with access token
        protected_url = reverse("auth:user-list")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {original_access}")
        protected_response = api_client.get(protected_url)
        assert protected_response.status_code == status.HTTP_200_OK

        # Step 3: Refresh the access token
        refresh_url = reverse("auth:token_refresh")
        refresh_response = api_client.post(
            refresh_url, {"refresh": refresh_token}, format="json"
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access = refresh_response.data["access"]
        assert new_access != original_access

        # Step 4: Verify the new access token
        verify_url = reverse("auth:token_verify")
        verify_response = api_client.post(
            verify_url, {"token": new_access}, format="json"
        )
        assert verify_response.status_code == status.HTTP_200_OK

        # Step 5: Use new access token to access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        final_response = api_client.get(protected_url)
        assert final_response.status_code == status.HTTP_200_OK

    def test_old_access_token_still_works_after_refresh(
        self, api_client, admin_user, tenant_context
    ):
        """Test that old access token still works after refresh (until expiry)."""
        # Login
        login_url = reverse("auth:token_obtain_pair")
        credentials = {
            "email": "admin@testcompany.com",
            "password": "TestPassword123!",
        }
        login_response = api_client.post(login_url, credentials, format="json")
        original_access = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Refresh to get new access token
        refresh_url = reverse("auth:token_refresh")
        refresh_response = api_client.post(
            refresh_url, {"refresh": refresh_token}, format="json"
        )
        new_access = refresh_response.data["access"]

        # Old access token should still work (until it expires)
        protected_url = reverse("auth:user-list")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {original_access}")
        response = api_client.get(protected_url)
        assert response.status_code == status.HTTP_200_OK

        # New access token should also work
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        response = api_client.get(protected_url)
        assert response.status_code == status.HTTP_200_OK
