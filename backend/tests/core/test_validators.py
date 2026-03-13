"""
Test suite for core validators module.

Tests cover:
- UUID validation (valid, invalid, None handling)
- UUID field validation for DRF views
- Multiple UUID validation
- Security sanitization for logging
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status

from apps.core.validators import (
    UUIDValidationError,
    sanitize_uuid_for_logging,
    validate_multiple_uuids,
    validate_uuid,
    validate_uuid_field,
)


class TestValidateUUID:
    """Tests for validate_uuid function."""

    def test_valid_uuid_string(self):
        """Test validating a valid UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(uuid_str)
        assert isinstance(result, uuid.UUID)
        assert str(result) == uuid_str

    def test_valid_uuid_object(self):
        """Test validating a UUID object."""
        uuid_obj = uuid.uuid4()
        result = validate_uuid(uuid_obj)
        assert result == uuid_obj

    def test_invalid_uuid_raises_error(self):
        """Test that invalid UUID raises UUIDValidationError."""
        with pytest.raises(UUIDValidationError) as exc_info:
            validate_uuid("not-a-valid-uuid")
        assert exc_info.value.field_name == "id"
        assert "Invalid UUID format" in str(exc_info.value)

    def test_none_without_allow_none_raises_error(self):
        """Test that None raises error when allow_none=False."""
        with pytest.raises(UUIDValidationError):
            validate_uuid(None, allow_none=False)

    def test_none_with_allow_none_returns_none(self):
        """Test that None returns None when allow_none=True."""
        result = validate_uuid(None, allow_none=True)
        assert result is None

    def test_empty_string_without_allow_none_raises_error(self):
        """Test that empty string raises error when allow_none=False."""
        with pytest.raises(UUIDValidationError):
            validate_uuid("", allow_none=False)

    def test_empty_string_with_allow_none_returns_none(self):
        """Test that empty string returns None when allow_none=True."""
        result = validate_uuid("   ", allow_none=True)
        assert result is None

    def test_custom_field_name_in_error(self):
        """Test that custom field name appears in error message."""
        with pytest.raises(UUIDValidationError) as exc_info:
            validate_uuid("invalid", field_name="product_id")
        assert exc_info.value.field_name == "product_id"
        assert "product_id" in str(exc_info.value)

    def test_integer_raises_error(self):
        """Test that integer raises UUIDValidationError."""
        with pytest.raises(UUIDValidationError):
            validate_uuid(12345)

    def test_uuid_with_hyphens(self):
        """Test UUID with hyphens is accepted."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(uuid_str)
        assert str(result) == uuid_str

    def test_uuid_without_hyphens(self):
        """Test UUID without hyphens is accepted."""
        uuid_str = "550e8400e29b41d4a716446655440000"
        result = validate_uuid(uuid_str)
        assert result is not None


class TestValidateUUIDField:
    """Tests for validate_uuid_field function."""

    def test_valid_required_field(self):
        """Test validating a valid required UUID field."""
        data = {"product_id": "550e8400-e29b-41d4-a716-446655440000"}
        is_valid, uuid_value, error = validate_uuid_field(data, "product_id", required=True)
        assert is_valid is True
        assert isinstance(uuid_value, uuid.UUID)
        assert error is None

    def test_missing_required_field(self):
        """Test that missing required field returns error response."""
        data = {}
        is_valid, uuid_value, error = validate_uuid_field(data, "product_id", required=True)
        assert is_valid is False
        assert uuid_value is None
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in error.data["message"].lower()

    def test_missing_optional_field(self):
        """Test that missing optional field returns valid with None."""
        data = {}
        is_valid, uuid_value, error = validate_uuid_field(data, "reference_id", required=False)
        assert is_valid is True
        assert uuid_value is None
        assert error is None

    def test_invalid_uuid_format(self):
        """Test that invalid UUID format returns error response."""
        data = {"product_id": "not-a-uuid"}
        is_valid, uuid_value, error = validate_uuid_field(data, "product_id", required=True)
        assert is_valid is False
        assert uuid_value is None
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid uuid" in error.data["message"].lower()

    def test_none_value_for_optional_field(self):
        """Test that None value for optional field is valid."""
        data = {"reference_id": None}
        is_valid, uuid_value, error = validate_uuid_field(data, "reference_id", required=False)
        assert is_valid is True
        assert uuid_value is None
        assert error is None


class TestValidateMultipleUUIDs:
    """Tests for validate_multiple_uuids function."""

    def test_all_valid_required_fields(self):
        """Test validating multiple valid required UUID fields."""
        data = {
            "product_id": "550e8400-e29b-41d4-a716-446655440000",
            "branch_id": "650e8400-e29b-41d4-a716-446655440001",
            "tenant_id": "750e8400-e29b-41d4-a716-446655440002",
        }
        field_specs = [
            {"name": "product_id", "required": True},
            {"name": "branch_id", "required": True},
            {"name": "tenant_id", "required": True},
        ]
        is_valid, values, error = validate_multiple_uuids(data, field_specs)
        assert is_valid is True
        assert len(values) == 3
        assert all(isinstance(v, uuid.UUID) for v in values.values())
        assert error is None

    def test_mixed_required_and_optional(self):
        """Test validating mix of required and optional fields."""
        data = {
            "product_id": "550e8400-e29b-41d4-a716-446655440000",
            "branch_id": "650e8400-e29b-41d4-a716-446655440001",
        }
        field_specs = [
            {"name": "product_id", "required": True},
            {"name": "branch_id", "required": True},
            {"name": "reference_id", "required": False},
        ]
        is_valid, values, error = validate_multiple_uuids(data, field_specs)
        assert is_valid is True
        assert len(values) == 3
        assert values["reference_id"] is None
        assert error is None

    def test_first_field_invalid(self):
        """Test that first invalid field stops validation and returns error."""
        data = {
            "product_id": "invalid-uuid",
            "branch_id": "650e8400-e29b-41d4-a716-446655440001",
        }
        field_specs = [
            {"name": "product_id", "required": True},
            {"name": "branch_id", "required": True},
        ]
        is_valid, values, error = validate_multiple_uuids(data, field_specs)
        assert is_valid is False
        assert values == {}
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_field(self):
        """Test that missing required field returns error."""
        data = {
            "product_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        field_specs = [
            {"name": "product_id", "required": True},
            {"name": "branch_id", "required": True},
        ]
        is_valid, values, error = validate_multiple_uuids(data, field_specs)
        assert is_valid is False
        assert values == {}
        assert error is not None


class TestSanitizeUUIDForLogging:
    """Tests for sanitize_uuid_for_logging function."""

    def test_valid_uuid_string(self):
        """Test sanitizing a valid UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = sanitize_uuid_for_logging(uuid_str)
        assert result == "550e8400-****"
        assert len(result) == 13

    def test_valid_uuid_object(self):
        """Test sanitizing a UUID object."""
        uuid_obj = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        result = sanitize_uuid_for_logging(uuid_obj)
        assert result == "550e8400-****"

    def test_none_value(self):
        """Test sanitizing None returns 'None'."""
        result = sanitize_uuid_for_logging(None)
        assert result == "None"

    def test_invalid_uuid(self):
        """Test sanitizing invalid UUID returns 'invalid-uuid'."""
        result = sanitize_uuid_for_logging("not-a-uuid")
        assert result == "invalid-uuid"

    def test_empty_string(self):
        """Test sanitizing empty string."""
        result = sanitize_uuid_for_logging("")
        assert result == "None"


class TestUUIDValidationErrorClass:
    """Tests for UUIDValidationError exception class."""

    def test_error_attributes(self):
        """Test that error stores field name and value."""
        error = UUIDValidationError("product_id", "invalid-value")
        assert error.field_name == "product_id"
        assert error.value == "invalid-value"
        assert "product_id" in str(error)
        assert "invalid-value" in str(error)

    def test_error_code(self):
        """Test that error has correct code."""
        error = UUIDValidationError("field", "value")
        # Check if error messages or code contain expected value
        assert "Invalid UUID format" in str(error)


# Security-focused tests
class TestUUIDValidationSecurity:
    """Security-focused tests for UUID validation."""

    def test_sql_injection_attempt(self):
        """Test that SQL injection attempts are rejected."""
        malicious_input = "'; DROP TABLE products; --"
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)

    def test_xss_attempt(self):
        """Test that XSS attempts are rejected."""
        malicious_input = "<script>alert('xss')</script>"
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)

    def test_path_traversal_attempt(self):
        """Test that path traversal attempts are rejected."""
        malicious_input = "../../etc/passwd"
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)

    def test_command_injection_attempt(self):
        """Test that command injection attempts are rejected."""
        malicious_input = "; rm -rf /"
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)

    def test_very_long_string(self):
        """Test that very long strings are rejected."""
        malicious_input = "a" * 10000
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)

    def test_null_byte_injection(self):
        """Test that null byte injection is rejected."""
        malicious_input = "550e8400\x00-e29b-41d4-a716-446655440000"
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)

    def test_unicode_homograph_attack(self):
        """Test that unicode homograph attacks are rejected."""
        # Using lookalike characters
        malicious_input = "550е8400-e29b-41d4-a716-446655440000"  # Cyrillic 'е'
        with pytest.raises(UUIDValidationError):
            validate_uuid(malicious_input)
