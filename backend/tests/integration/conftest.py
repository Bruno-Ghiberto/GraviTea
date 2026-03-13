"""
Integration test fixtures for Gravitea ERP.

Extends base conftest fixtures with:
- RFC 7807 Problem Details response validation
- Health check endpoint testing
- Trace ID correlation testing
- Error response contract validation

Per spec.md FR-019 through FR-023 requirements.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.exceptions.trace import clear_trace_context, set_trace_context, TraceContext


# ============================================================
# RFC 7807 Problem Details Fixtures
# ============================================================


@pytest.fixture
def problem_detail_validator():
    """Validator for RFC 7807 Problem Details responses.

    Returns a callable that validates response data against RFC 7807 spec.
    """

    def validate(
        response_data: dict[str, Any],
        *,
        expected_status: int | None = None,
        expected_type_suffix: str | None = None,
        expect_errors: bool = False,
    ) -> None:
        """Validate RFC 7807 Problem Details response.

        Args:
            response_data: Response JSON data to validate
            expected_status: Expected HTTP status code in response
            expected_type_suffix: Expected type URI suffix (e.g., "validation-error")
            expect_errors: Whether to expect field errors array

        Raises:
            AssertionError: If validation fails
        """
        # Required fields per RFC 7807
        assert "type" in response_data, "Missing required field: type"
        assert "title" in response_data, "Missing required field: title"
        assert "status" in response_data, "Missing required field: status"
        assert "detail" in response_data, "Missing required field: detail"
        assert "trace_id" in response_data, "Missing required field: trace_id"

        # Type must be a URI
        assert response_data["type"].startswith("https://"), "type must be a URI"

        # Status must be integer
        assert isinstance(response_data["status"], int), "status must be integer"

        # Trace ID must be valid UUID
        try:
            uuid.UUID(response_data["trace_id"])
        except ValueError:
            pytest.fail("trace_id must be a valid UUID")

        # Validate title length
        assert len(response_data["title"]) <= 100, "title must be ≤100 characters"

        # Validate detail length
        assert len(response_data["detail"]) <= 500, "detail must be ≤500 characters"

        # Optional validations
        if expected_status is not None:
            assert response_data["status"] == expected_status, (
                f"Expected status {expected_status}, got {response_data['status']}"
            )

        if expected_type_suffix is not None:
            assert response_data["type"].endswith(expected_type_suffix), (
                f"Expected type ending with {expected_type_suffix}, got {response_data['type']}"
            )

        if expect_errors:
            assert "errors" in response_data, "Expected errors array"
            assert isinstance(response_data["errors"], list), "errors must be a list"
            for error in response_data["errors"]:
                assert "field" in error, "Field error missing 'field'"
                assert "message" in error, "Field error missing 'message'"
                assert "code" in error, "Field error missing 'code'"

    return validate


@pytest.fixture
def field_error_validator():
    """Validator for field-level errors in Problem Details.

    Returns a callable that validates a single field error.
    """

    def validate(
        error: dict[str, Any],
        *,
        expected_field: str | None = None,
        expected_code: str | None = None,
    ) -> None:
        """Validate a single field error.

        Args:
            error: Field error dict to validate
            expected_field: Expected field name (supports dot notation)
            expected_code: Expected error code

        Raises:
            AssertionError: If validation fails
        """
        assert "field" in error, "Field error missing 'field'"
        assert "message" in error, "Field error missing 'message'"
        assert "code" in error, "Field error missing 'code'"

        if expected_field is not None:
            assert error["field"] == expected_field, (
                f"Expected field '{expected_field}', got '{error['field']}'"
            )

        if expected_code is not None:
            assert error["code"] == expected_code, (
                f"Expected code '{expected_code}', got '{error['code']}'"
            )

    return validate


# ============================================================
# Trace Context Fixtures
# ============================================================


@pytest.fixture
def trace_context():
    """Create and manage a test trace context.

    Yields a TraceContext and cleans up after the test.
    """
    ctx = TraceContext(
        trace_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        branch_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        request_path="/api/v1/test",
        request_method="GET",
    )
    set_trace_context(ctx)
    yield ctx
    clear_trace_context()


@pytest.fixture
def trace_id_client(api_client):
    """API client that captures trace IDs from responses.

    Returns a client wrapper with trace_id extraction.
    """

    class TraceIdClient:
        """API client wrapper with trace ID tracking."""

        def __init__(self, client: APIClient):
            self._client = client
            self.last_trace_id: str | None = None

        def _extract_trace_id(self, response):
            """Extract trace ID from response headers."""
            self.last_trace_id = response.get("X-Trace-ID")
            return response

        def get(self, *args, **kwargs):
            """GET request with trace ID extraction."""
            return self._extract_trace_id(self._client.get(*args, **kwargs))

        def post(self, *args, **kwargs):
            """POST request with trace ID extraction."""
            return self._extract_trace_id(self._client.post(*args, **kwargs))

        def put(self, *args, **kwargs):
            """PUT request with trace ID extraction."""
            return self._extract_trace_id(self._client.put(*args, **kwargs))

        def patch(self, *args, **kwargs):
            """PATCH request with trace ID extraction."""
            return self._extract_trace_id(self._client.patch(*args, **kwargs))

        def delete(self, *args, **kwargs):
            """DELETE request with trace ID extraction."""
            return self._extract_trace_id(self._client.delete(*args, **kwargs))

        def credentials(self, *args, **kwargs):
            """Pass through credentials."""
            return self._client.credentials(*args, **kwargs)

    return TraceIdClient(api_client)


# ============================================================
# Health Check Fixtures
# ============================================================


@pytest.fixture
def health_check_client(api_client):
    """Unauthenticated client for health check endpoints.

    Health endpoints should not require authentication per Kubernetes probe specs.
    """
    return api_client


@pytest.fixture
def health_response_validator():
    """Validator for health check responses.

    Returns a callable that validates health response structure.
    """

    def validate(
        response_data: dict[str, Any],
        *,
        expected_status: str = "healthy",
        expect_checks: bool = False,
        expected_checks: list[str] | None = None,
    ) -> None:
        """Validate health check response.

        Args:
            response_data: Response JSON data to validate
            expected_status: Expected overall status
            expect_checks: Whether to expect dependency checks
            expected_checks: List of expected check names

        Raises:
            AssertionError: If validation fails
        """
        assert "status" in response_data, "Missing required field: status"
        assert response_data["status"] in ("healthy", "unhealthy"), (
            f"Invalid status: {response_data['status']}"
        )

        if expected_status is not None:
            assert response_data["status"] == expected_status, (
                f"Expected status '{expected_status}', got '{response_data['status']}'"
            )

        if expect_checks:
            assert "checks" in response_data, "Expected checks dict"
            assert isinstance(response_data["checks"], dict), "checks must be a dict"

            for check_name, check_data in response_data["checks"].items():
                assert "status" in check_data, f"Check '{check_name}' missing status"
                if check_data["status"] == "healthy":
                    assert "latency_ms" in check_data, (
                        f"Healthy check '{check_name}' missing latency_ms"
                    )
                elif check_data["status"] == "unhealthy":
                    assert "error" in check_data, (
                        f"Unhealthy check '{check_name}' missing error"
                    )

        if expected_checks is not None:
            assert "checks" in response_data, "Expected checks dict"
            for check_name in expected_checks:
                assert check_name in response_data["checks"], (
                    f"Missing expected check: {check_name}"
                )

    return validate


# ============================================================
# Error Response Fixtures
# ============================================================


@pytest.fixture
def error_response_fixtures():
    """Common error response test cases.

    Returns dict of test scenarios for error handling.
    """
    return {
        "validation_error": {
            "expected_status": 400,
            "expected_type": "validation-error",
            "expect_errors": True,
        },
        "authentication_error": {
            "expected_status": 401,
            "expected_type": "unauthorized",
            "expect_errors": False,
        },
        "permission_error": {
            "expected_status": 403,
            "expected_type": "forbidden",
            "expect_errors": False,
        },
        "not_found": {
            "expected_status": 404,
            "expected_type": "not-found",
            "expect_errors": False,
        },
        "method_not_allowed": {
            "expected_status": 405,
            "expected_type": "method-not-allowed",
            "expect_errors": False,
        },
        "conflict": {
            "expected_status": 409,
            "expected_type": "conflict",
            "expect_errors": False,
        },
        "rate_limit": {
            "expected_status": 429,
            "expected_type": "rate-limit-exceeded",
            "expect_errors": False,
        },
        "server_error": {
            "expected_status": 500,
            "expected_type": "internal-server-error",
            "expect_errors": False,
        },
    }


# ============================================================
# Response Assertion Helpers
# ============================================================


@pytest.fixture
def assert_problem_detail():
    """Assertion helper for Problem Details responses.

    Returns a callable that asserts response is valid Problem Details.
    """

    def _assert(response, *, expected_status: int, expected_type_suffix: str):
        """Assert response is a valid Problem Details response.

        Args:
            response: DRF Response object
            expected_status: Expected HTTP status code
            expected_type_suffix: Expected type URI suffix
        """
        assert response.status_code == expected_status
        assert response["Content-Type"] == "application/problem+json"

        data = response.json()
        assert data["status"] == expected_status
        assert data["type"].endswith(expected_type_suffix)
        assert "trace_id" in data

    return _assert


@pytest.fixture
def assert_health_response():
    """Assertion helper for health check responses.

    Returns a callable that asserts response is valid health response.
    """

    def _assert(
        response,
        *,
        expected_http_status: int = 200,
        expected_health_status: str = "healthy",
    ):
        """Assert response is a valid health check response.

        Args:
            response: DRF Response object
            expected_http_status: Expected HTTP status code
            expected_health_status: Expected health status string
        """
        assert response.status_code == expected_http_status
        data = response.json()
        assert data["status"] == expected_health_status

    return _assert
