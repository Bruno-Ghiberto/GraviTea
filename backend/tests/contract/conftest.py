"""
Contract test fixtures for Gravitea ERP.

Provides fixtures for API contract validation:
- OpenAPI schema validation
- Response structure contracts
- Error response contracts
- Pagination contracts

Per spec.md API Contract Validation requirements.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from rest_framework.test import APIClient


# ============================================================
# OpenAPI Schema Fixtures
# ============================================================


@pytest.fixture(scope="session")
def openapi_schema(django_db_setup, django_db_blocker):
    """Load OpenAPI schema from the schema endpoint.

    Returns the parsed OpenAPI schema dict.
    """
    with django_db_blocker.unblock():
        client = APIClient()
        response = client.get("/api/v1/schema/")
        assert response.status_code == 200, f"Failed to load schema: {response.status_code}"
        return response.json()


@pytest.fixture
def schema_validator(openapi_schema):
    """Validator for response against OpenAPI schema.

    Returns a callable that validates responses against schema definitions.
    """

    def get_schema_for_path(path: str, method: str, status_code: int) -> dict | None:
        """Get response schema for a given path, method, and status code.

        Args:
            path: API path (e.g., "/api/v1/products/")
            method: HTTP method (lowercase)
            status_code: HTTP status code

        Returns:
            Schema dict or None if not found
        """
        paths = openapi_schema.get("paths", {})

        # Normalize path
        if not path.startswith("/"):
            path = "/" + path

        # Try exact match first
        path_schema = paths.get(path)

        # Try with trailing slash variations
        if path_schema is None:
            alt_path = path.rstrip("/") if path.endswith("/") else path + "/"
            path_schema = paths.get(alt_path)

        if path_schema is None:
            return None

        method_schema = path_schema.get(method.lower())
        if method_schema is None:
            return None

        responses = method_schema.get("responses", {})
        status_schema = responses.get(str(status_code), responses.get("default"))

        if status_schema is None:
            return None

        # Get content schema
        content = status_schema.get("content", {})
        json_content = content.get("application/json", content.get("application/problem+json"))

        if json_content is None:
            return None

        return json_content.get("schema")

    def validate(
        response_data: dict[str, Any],
        *,
        path: str,
        method: str,
        status_code: int,
    ) -> list[str]:
        """Validate response against OpenAPI schema.

        Args:
            response_data: Response JSON data
            path: API path
            method: HTTP method
            status_code: HTTP status code

        Returns:
            List of validation errors (empty if valid)
        """
        schema = get_schema_for_path(path, method, status_code)
        if schema is None:
            return [f"No schema found for {method.upper()} {path} {status_code}"]

        errors = []

        # Validate required properties
        required = schema.get("required", [])
        for prop in required:
            if prop not in response_data:
                errors.append(f"Missing required property: {prop}")

        # Validate property types
        properties = schema.get("properties", {})
        for prop, value in response_data.items():
            if prop in properties:
                prop_schema = properties[prop]
                expected_type = prop_schema.get("type")
                if expected_type:
                    actual_type = _get_json_type(value)
                    if actual_type != expected_type and not (
                        expected_type == "integer" and actual_type == "number"
                    ):
                        errors.append(
                            f"Property '{prop}' expected type '{expected_type}', "
                            f"got '{actual_type}'"
                        )

        return errors

    return validate


def _get_json_type(value: Any) -> str:
    """Get JSON type name for a Python value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


# ============================================================
# Response Contract Fixtures
# ============================================================


@pytest.fixture
def list_response_contract():
    """Contract validator for paginated list responses.

    Returns a callable that validates list response structure.
    """

    def validate(
        response_data: dict[str, Any],
        *,
        item_validator: callable | None = None,
    ) -> list[str]:
        """Validate paginated list response contract.

        Args:
            response_data: Response JSON data
            item_validator: Optional callable to validate each item

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Cursor pagination uses next/previous/results
        if "results" not in response_data:
            errors.append("Missing 'results' array in paginated response")
            return errors

        if not isinstance(response_data["results"], list):
            errors.append("'results' must be an array")
            return errors

        # Validate cursor pagination fields
        if "next" not in response_data:
            errors.append("Missing 'next' cursor field")
        if "previous" not in response_data:
            errors.append("Missing 'previous' cursor field")

        # Validate each item if validator provided
        if item_validator and not errors:
            for i, item in enumerate(response_data["results"]):
                item_errors = item_validator(item)
                for err in item_errors:
                    errors.append(f"Item {i}: {err}")

        return errors

    return validate


@pytest.fixture
def detail_response_contract():
    """Contract validator for single object detail responses.

    Returns a callable that validates detail response structure.
    """

    def validate(
        response_data: dict[str, Any],
        *,
        required_fields: list[str] | None = None,
        field_types: dict[str, str] | None = None,
    ) -> list[str]:
        """Validate detail response contract.

        Args:
            response_data: Response JSON data
            required_fields: List of required field names
            field_types: Dict mapping field names to expected types

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Must be an object
        if not isinstance(response_data, dict):
            errors.append("Detail response must be an object")
            return errors

        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in response_data:
                    errors.append(f"Missing required field: {field}")

        # Check field types
        if field_types:
            for field, expected_type in field_types.items():
                if field in response_data:
                    actual_type = _get_json_type(response_data[field])
                    if actual_type != expected_type:
                        errors.append(
                            f"Field '{field}' expected type '{expected_type}', "
                            f"got '{actual_type}'"
                        )

        return errors

    return validate


# ============================================================
# Error Contract Fixtures
# ============================================================


@pytest.fixture
def problem_detail_contract():
    """Contract validator for RFC 7807 Problem Details.

    Returns a callable that validates Problem Details structure.
    """

    def validate(response_data: dict[str, Any]) -> list[str]:
        """Validate RFC 7807 Problem Details contract.

        Args:
            response_data: Response JSON data

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields per RFC 7807 + our extensions
        required_fields = ["type", "title", "status", "detail", "trace_id"]
        for field in required_fields:
            if field not in response_data:
                errors.append(f"Missing required Problem Details field: {field}")

        if errors:
            return errors

        # Type must be URI
        if not response_data["type"].startswith("https://"):
            errors.append("'type' must be a URI (starting with https://)")

        # Status must be integer
        if not isinstance(response_data["status"], int):
            errors.append("'status' must be an integer")
        elif not (400 <= response_data["status"] < 600):
            errors.append("'status' must be an HTTP error status (400-599)")

        # Title length
        if len(response_data["title"]) > 100:
            errors.append("'title' must be ≤100 characters")

        # Detail length
        if len(response_data["detail"]) > 500:
            errors.append("'detail' must be ≤500 characters")

        # Validate errors array if present
        if "errors" in response_data:
            if not isinstance(response_data["errors"], list):
                errors.append("'errors' must be an array")
            else:
                for i, field_error in enumerate(response_data["errors"]):
                    if not isinstance(field_error, dict):
                        errors.append(f"errors[{i}] must be an object")
                        continue
                    if "field" not in field_error:
                        errors.append(f"errors[{i}] missing 'field'")
                    if "message" not in field_error:
                        errors.append(f"errors[{i}] missing 'message'")
                    if "code" not in field_error:
                        errors.append(f"errors[{i}] missing 'code'")

        return errors

    return validate


@pytest.fixture
def error_code_contract():
    """Contract for standard error codes.

    Returns mapping of HTTP status to expected error type suffixes.
    """
    return {
        400: "validation-error",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        405: "method-not-allowed",
        409: "conflict",
        422: "unprocessable-entity",
        429: "rate-limit-exceeded",
        500: "internal-server-error",
        503: "service-unavailable",
    }


# ============================================================
# Health Check Contract Fixtures
# ============================================================


@pytest.fixture
def health_check_contract():
    """Contract validator for health check responses.

    Returns a callable that validates health response structure.
    """

    def validate(
        response_data: dict[str, Any],
        *,
        expected_checks: list[str] | None = None,
    ) -> list[str]:
        """Validate health check response contract.

        Args:
            response_data: Response JSON data
            expected_checks: List of expected check names

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required field
        if "status" not in response_data:
            errors.append("Missing required field: status")
            return errors

        # Status must be valid
        if response_data["status"] not in ("healthy", "unhealthy"):
            errors.append(f"Invalid status: {response_data['status']}")

        # Validate checks if present
        if "checks" in response_data:
            if not isinstance(response_data["checks"], dict):
                errors.append("'checks' must be an object")
            else:
                for name, check in response_data["checks"].items():
                    if "status" not in check:
                        errors.append(f"Check '{name}' missing 'status'")
                    elif check["status"] not in ("healthy", "unhealthy"):
                        errors.append(f"Check '{name}' has invalid status")
                    elif check["status"] == "healthy":
                        if "latency_ms" not in check:
                            errors.append(f"Healthy check '{name}' missing 'latency_ms'")
                        elif not isinstance(check["latency_ms"], (int, float)):
                            errors.append(f"Check '{name}' latency_ms must be numeric")
                    elif check["status"] == "unhealthy":
                        if "error" not in check:
                            errors.append(f"Unhealthy check '{name}' missing 'error'")

        # Validate expected checks
        if expected_checks:
            if "checks" not in response_data:
                errors.append("Expected 'checks' object")
            else:
                for check_name in expected_checks:
                    if check_name not in response_data["checks"]:
                        errors.append(f"Missing expected check: {check_name}")

        return errors

    return validate


# ============================================================
# Pagination Contract Fixtures
# ============================================================


@pytest.fixture
def cursor_pagination_contract():
    """Contract validator for cursor-based pagination.

    Returns a callable that validates cursor pagination structure.
    """

    def validate(response_data: dict[str, Any]) -> list[str]:
        """Validate cursor pagination contract.

        Args:
            response_data: Response JSON data

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields for cursor pagination
        required_fields = ["next", "previous", "results"]
        for field in required_fields:
            if field not in response_data:
                errors.append(f"Missing cursor pagination field: {field}")

        if errors:
            return errors

        # next/previous must be string or null
        for field in ["next", "previous"]:
            value = response_data[field]
            if value is not None and not isinstance(value, str):
                errors.append(f"'{field}' must be string or null")

        # results must be array
        if not isinstance(response_data["results"], list):
            errors.append("'results' must be an array")

        return errors

    return validate


# ============================================================
# Assertion Helpers
# ============================================================


@pytest.fixture
def assert_contract_valid():
    """Assertion helper for contract validation.

    Returns a callable that asserts contract validation passes.
    """

    def _assert(errors: list[str], context: str = ""):
        """Assert contract validation passes.

        Args:
            errors: List of validation errors
            context: Optional context for error message

        Raises:
            AssertionError: If there are validation errors
        """
        if errors:
            prefix = f"{context}: " if context else ""
            error_list = "\n  - ".join(errors)
            pytest.fail(f"{prefix}Contract validation failed:\n  - {error_list}")

    return _assert


@pytest.fixture
def assert_response_matches_contract(
    assert_contract_valid,
    problem_detail_contract,
    cursor_pagination_contract,
):
    """High-level assertion helper for common response contracts.

    Returns a callable that validates common response patterns.
    """

    def _assert(
        response,
        *,
        contract_type: str,
        expected_status: int | None = None,
    ):
        """Assert response matches expected contract.

        Args:
            response: DRF Response object
            contract_type: One of 'problem_detail', 'paginated_list', 'detail'
            expected_status: Expected HTTP status code

        Raises:
            AssertionError: If contract validation fails
        """
        if expected_status is not None:
            assert response.status_code == expected_status, (
                f"Expected status {expected_status}, got {response.status_code}"
            )

        data = response.json()

        if contract_type == "problem_detail":
            errors = problem_detail_contract(data)
            assert_contract_valid(errors, f"Problem Detail response (HTTP {response.status_code})")

        elif contract_type == "paginated_list":
            errors = cursor_pagination_contract(data)
            assert_contract_valid(errors, "Paginated list response")

        elif contract_type == "detail":
            if not isinstance(data, dict):
                pytest.fail("Detail response must be an object")

        else:
            pytest.fail(f"Unknown contract type: {contract_type}")

    return _assert
