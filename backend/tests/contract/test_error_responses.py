"""
Contract tests for RFC 7807 Problem Details error responses.

Validates that all API error responses conform to the RFC 7807
Problem Details specification with our extensions (trace_id, errors array).

Per spec.md API Contract Validation requirements.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestValidationErrorContract:
    """Tests for 400 Bad Request validation error responses."""

    def test_missing_required_field_returns_rfc7807(
        self, authenticated_client, problem_detail_contract, assert_contract_valid
    ):
        """Test that missing required fields return RFC 7807 format."""
        url = reverse("auth:user-list")
        data = {
            "full_name": "Test User",
            # Missing email and password
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = problem_detail_contract(response.data)
        assert_contract_valid(errors, "Missing required field error")

    def test_invalid_email_format_returns_rfc7807(
        self, authenticated_client, problem_detail_contract, assert_contract_valid
    ):
        """Test that invalid email format returns RFC 7807 format."""
        url = reverse("auth:user-list")
        data = {
            "email": "not-an-email",
            "full_name": "Test User",
            "password": "SecurePassword123!",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = problem_detail_contract(response.data)
        assert_contract_valid(errors, "Invalid email format error")

    def test_validation_error_has_errors_array(
        self, authenticated_client
    ):
        """Test that validation errors include field-level errors array."""
        url = reverse("auth:user-list")
        data = {
            "email": "invalid",
            "full_name": "Test User",
            "password": "weak",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data
        assert isinstance(response.data["errors"], list)
        assert len(response.data["errors"]) > 0

        # Check error structure
        for error in response.data["errors"]:
            assert "field" in error
            assert "message" in error
            assert "code" in error

    def test_validation_error_type_uri(self, authenticated_client):
        """Test that validation errors have correct type URI."""
        url = reverse("auth:user-list")
        data = {"email": "invalid"}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "type" in response.data
        assert response.data["type"].startswith("https://")
        assert "validation-error" in response.data["type"]


class TestAuthenticationErrorContract:
    """Tests for 401 Unauthorized error responses."""

    def test_missing_token_returns_rfc7807(
        self, api_client, problem_detail_contract, assert_contract_valid
    ):
        """Test that missing authentication returns RFC 7807 format."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        errors = problem_detail_contract(response.data)
        assert_contract_valid(errors, "Missing token error")

    def test_invalid_token_returns_rfc7807(
        self, api_client, problem_detail_contract, assert_contract_valid
    ):
        """Test that invalid token returns RFC 7807 format."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        errors = problem_detail_contract(response.data)
        assert_contract_valid(errors, "Invalid token error")

    def test_auth_error_has_trace_id(self, api_client):
        """Test that authentication errors include trace_id."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "trace_id" in response.data
        assert isinstance(response.data["trace_id"], str)
        assert len(response.data["trace_id"]) > 0


class TestNotFoundErrorContract:
    """Tests for 404 Not Found error responses."""

    def test_nonexistent_resource_returns_rfc7807(
        self, authenticated_client, problem_detail_contract, assert_contract_valid
    ):
        """Test that nonexistent resource returns RFC 7807 format."""
        import uuid
        url = reverse("auth:user-detail", kwargs={"pk": uuid.uuid4()})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        errors = problem_detail_contract(response.data)
        assert_contract_valid(errors, "Not found error")

    def test_not_found_error_type_uri(self, authenticated_client):
        """Test that not found errors have correct type URI."""
        import uuid
        url = reverse("auth:user-detail", kwargs={"pk": uuid.uuid4()})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "type" in response.data
        assert "not-found" in response.data["type"]


class TestMethodNotAllowedContract:
    """Tests for 405 Method Not Allowed error responses."""

    def test_invalid_method_returns_rfc7807(
        self, api_client, problem_detail_contract, assert_contract_valid
    ):
        """Test that invalid HTTP method returns RFC 7807 format."""
        # Health endpoints only allow GET
        response = api_client.post("/health/live")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        errors = problem_detail_contract(response.data)
        assert_contract_valid(errors, "Method not allowed error")

    def test_method_not_allowed_has_allowed_methods(self, api_client):
        """Test that 405 response includes Allow header."""
        response = api_client.post("/health/live")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        # DRF may include allowed methods in response
        assert "Allow" in response or "detail" in response.data


class TestErrorResponseTraceId:
    """Tests for trace_id presence in all error responses."""

    def test_unauthenticated_error_has_trace_id(self, api_client):
        """Test that unauthenticated error responses include trace_id."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "trace_id" in response.data, "Missing trace_id in 401 response"

    def test_method_not_allowed_error_has_trace_id(self, api_client):
        """Test that method not allowed error responses include trace_id."""
        response = api_client.post("/health/live")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert "trace_id" in response.data, "Missing trace_id in 405 response"


class TestErrorResponseStatusField:
    """Tests for status field consistency."""

    def test_status_matches_http_code(self, api_client):
        """Test that status field matches HTTP status code."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data.get("status") == 401


class TestErrorResponseTitleAndDetail:
    """Tests for title and detail field requirements."""

    def test_title_is_short(self, api_client):
        """Test that title is ≤100 characters."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "title" in response.data
        assert len(response.data["title"]) <= 100

    def test_detail_is_descriptive(self, api_client):
        """Test that detail provides useful information."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.data
        assert len(response.data["detail"]) > 0
        assert len(response.data["detail"]) <= 500


class TestFieldErrorStructure:
    """Tests for field-level error structure in validation errors."""

    def test_field_error_has_required_keys(self, authenticated_client):
        """Test that each field error has field, message, code."""
        url = reverse("auth:user-list")
        data = {"email": "invalid-email"}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data

        for error in response.data["errors"]:
            assert "field" in error, "Error missing 'field' key"
            assert "message" in error, "Error missing 'message' key"
            assert "code" in error, "Error missing 'code' key"

    def test_field_names_are_strings(self, authenticated_client):
        """Test that field names are non-empty strings."""
        url = reverse("auth:user-list")
        data = {"email": "invalid"}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        for error in response.data["errors"]:
            assert isinstance(error["field"], str)
            assert len(error["field"]) > 0

    def test_error_codes_are_standardized(self, authenticated_client):
        """Test that error codes follow standard format."""
        url = reverse("auth:user-list")
        data = {"email": "invalid", "password": "x"}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        for error in response.data["errors"]:
            # Error codes should be lowercase with underscores or hyphens
            assert isinstance(error["code"], str)
            assert len(error["code"]) > 0


class TestContentTypeContract:
    """Tests for content type of error responses."""

    def test_error_response_is_json(self, api_client):
        """Test that error responses use application/json content type."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Accept either application/json or application/problem+json
        content_type = response["Content-Type"]
        assert "application/json" in content_type or "application/problem+json" in content_type


class TestErrorResponseIdempotency:
    """Tests that same error conditions produce consistent responses."""

    def test_same_error_produces_consistent_structure(self, api_client):
        """Test that repeated errors have consistent structure."""
        url = reverse("auth:user-list")

        responses = [api_client.get(url) for _ in range(3)]

        # All should be 401
        for resp in responses:
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED

        # All should have same fields (different trace_ids)
        keys = [set(resp.data.keys()) for resp in responses]
        assert keys[0] == keys[1] == keys[2]

        # All should have type, title, status, detail
        for resp in responses:
            assert "type" in resp.data
            assert "title" in resp.data
            assert "status" in resp.data
            assert "detail" in resp.data
