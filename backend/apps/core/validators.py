"""
Core validation utilities for Gravitea ERP.

Provides reusable validators for common data types and business logic,
including password complexity enforcement per security hardening requirements.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Optional, Tuple

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# =============================================================================
# PASSWORD COMPLEXITY VALIDATOR
# =============================================================================


class PasswordComplexityValidator:
    """
    Validate password meets complexity requirements for security hardening.

    Requirements (P2 security hardening):
    - Minimum 12 characters
    - At least 1 uppercase letter (A-Z)
    - At least 1 lowercase letter (a-z)
    - At least 1 digit (0-9)
    - At least 1 special character (!@#$%^&*(),.?":{}|<>-_=+[]\\;'`~/)

    This validator is designed to work with Django's AUTH_PASSWORD_VALIDATORS
    setting and provides clear, user-friendly error messages.
    """

    SPECIAL_CHARACTERS = r"""!@#$%^&*(),.?":{}|<>\-_=+[\]\\;'`~/"""

    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
    ) -> None:
        """
        Initialize validator with configurable requirements.

        Args:
            min_length: Minimum password length (default: 12)
            require_uppercase: Require at least one uppercase letter
            require_lowercase: Require at least one lowercase letter
            require_digit: Require at least one digit
            require_special: Require at least one special character
        """
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special

    def validate(self, password: str, user: Any = None) -> None:
        """
        Validate the password meets complexity requirements.

        Args:
            password: The password to validate
            user: The user model instance (unused, but required by Django API)

        Raises:
            ValidationError: If the password does not meet requirements
        """
        errors = []

        # Check minimum length
        if len(password) < self.min_length:
            errors.append(
                ValidationError(
                    _("Password must be at least %(min_length)d characters long."),
                    code="password_too_short",
                    params={"min_length": self.min_length},
                )
            )

        # Check for uppercase letter
        if self.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one uppercase letter (A-Z)."),
                    code="password_no_uppercase",
                )
            )

        # Check for lowercase letter
        if self.require_lowercase and not re.search(r"[a-z]", password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one lowercase letter (a-z)."),
                    code="password_no_lowercase",
                )
            )

        # Check for digit
        if self.require_digit and not re.search(r"\d", password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one digit (0-9)."),
                    code="password_no_digit",
                )
            )

        # Check for special character
        if self.require_special:
            # Use a character class that includes common special characters
            special_pattern = r"""[!@#$%^&*()\-_=+\[\]{}\\|;:'",.<>/?`~]"""
            if not re.search(special_pattern, password):
                errors.append(
                    ValidationError(
                        _(
                            "Password must contain at least one special character "
                            "(e.g., !@#$%^&*()-_=+[]{}|;:'\",.<>/?`~)."
                        ),
                        code="password_no_special",
                    )
                )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self) -> str:
        """
        Return a description of the password requirements.

        Returns:
            Human-readable description of password requirements.
        """
        requirements = []

        if self.min_length > 0:
            requirements.append(f"at least {self.min_length} characters")

        if self.require_uppercase:
            requirements.append("one uppercase letter")

        if self.require_lowercase:
            requirements.append("one lowercase letter")

        if self.require_digit:
            requirements.append("one digit")

        if self.require_special:
            requirements.append("one special character")

        if not requirements:
            return ""

        return _(
            "Your password must contain %(requirements)s."
        ) % {"requirements": ", ".join(requirements)}


class UUIDValidationError(ValidationError):
    """Raised when UUID validation fails."""

    def __init__(self, field_name: str, value: Any):
        self.field_name = field_name
        self.value = value
        super().__init__(
            f"Invalid UUID format for {field_name}: {value}",
            code="invalid_uuid",
        )


def validate_uuid(
    value: Any,
    field_name: str = "id",
    allow_none: bool = False,
) -> Optional[uuid.UUID]:
    """
    Validate and convert a UUID value.

    Args:
        value: Value to validate (can be str, UUID, or None)
        field_name: Name of the field being validated (for error messages)
        allow_none: Whether to allow None values

    Returns:
        UUID object if valid, None if value is None and allow_none=True

    Raises:
        UUIDValidationError: If the value is not a valid UUID

    Examples:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        UUID('550e8400-e29b-41d4-a716-446655440000')

        >>> validate_uuid(None, allow_none=True)
        None

        >>> validate_uuid("invalid-uuid")
        UUIDValidationError: Invalid UUID format for id: invalid-uuid
    """
    # Handle None values
    if value is None:
        if allow_none:
            return None
        raise UUIDValidationError(field_name, value)

    # Handle empty strings
    if isinstance(value, str) and not value.strip():
        if allow_none:
            return None
        raise UUIDValidationError(field_name, value)

    # If already a UUID object, validate it
    if isinstance(value, uuid.UUID):
        return value

    # Try to convert string to UUID
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning(
            f"UUID validation failed for {field_name}: {value} - {str(e)}",
            extra={"field_name": field_name, "value": value, "error": str(e)},
        )
        raise UUIDValidationError(field_name, value)


def validate_uuid_field(
    data: dict,
    field_name: str,
    required: bool = True,
) -> Tuple[bool, Optional[uuid.UUID], Optional[Response]]:
    """
    Validate a UUID field from request data and return a REST response if invalid.

    This is a convenience function for use in DRF views/viewsets.

    Args:
        data: Request data dictionary
        field_name: Name of the UUID field to validate
        required: Whether the field is required

    Returns:
        Tuple of (is_valid, uuid_value, error_response)
        - is_valid: True if validation passed
        - uuid_value: The validated UUID or None
        - error_response: DRF Response object if validation failed, None otherwise

    Examples:
        >>> # In a DRF view
        >>> is_valid, product_id, error = validate_uuid_field(
        ...     request.data, 'product_id', required=True
        ... )
        >>> if not is_valid:
        ...     return error  # Returns 400 error response
        >>> # Continue with valid product_id
    """
    # Check if field exists
    value = data.get(field_name)

    if value is None:
        if required:
            return (
                False,
                None,
                Response(
                    {
                        "error": "validation_error",
                        "field": field_name,
                        "message": f"Field '{field_name}' is required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )
        return (True, None, None)

    # Validate UUID format
    try:
        uuid_value = validate_uuid(value, field_name, allow_none=not required)
        return (True, uuid_value, None)
    except UUIDValidationError as e:
        return (
            False,
            None,
            Response(
                {
                    "error": "validation_error",
                    "field": field_name,
                    "message": f"Invalid UUID format for '{field_name}': {value}",
                    "code": "invalid_uuid",
                },
                status=status.HTTP_400_BAD_REQUEST,
            ),
        )


def validate_multiple_uuids(
    data: dict,
    field_specs: list[dict],
) -> Tuple[bool, dict, Optional[Response]]:
    """
    Validate multiple UUID fields at once.

    Args:
        data: Request data dictionary
        field_specs: List of field specifications, each containing:
            - name: Field name
            - required: Whether field is required (default: True)

    Returns:
        Tuple of (is_valid, validated_values, error_response)
        - is_valid: True if all validations passed
        - validated_values: Dict of {field_name: uuid_value}
        - error_response: DRF Response if any validation failed

    Examples:
        >>> is_valid, values, error = validate_multiple_uuids(
        ...     request.data,
        ...     [
        ...         {'name': 'product_id', 'required': True},
        ...         {'name': 'branch_id', 'required': True},
        ...         {'name': 'reference_id', 'required': False},
        ...     ]
        ... )
        >>> if not is_valid:
        ...     return error
        >>> product_id = values['product_id']
        >>> branch_id = values['branch_id']
    """
    validated_values = {}

    for field_spec in field_specs:
        field_name = field_spec["name"]
        required = field_spec.get("required", True)

        is_valid, uuid_value, error_response = validate_uuid_field(
            data, field_name, required
        )

        if not is_valid:
            return (False, {}, error_response)

        validated_values[field_name] = uuid_value

    return (True, validated_values, None)


# Security utilities
def sanitize_uuid_for_logging(value: Any) -> str:
    """
    Sanitize UUID for safe logging (first 8 chars only).

    Args:
        value: UUID value to sanitize

    Returns:
        Sanitized string safe for logging

    Examples:
        >>> sanitize_uuid_for_logging("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-****'
    """
    try:
        uuid_obj = validate_uuid(value, "value", allow_none=True)
        if uuid_obj is None:
            return "None"
        uuid_str = str(uuid_obj)
        return f"{uuid_str[:8]}-****"
    except UUIDValidationError:
        return "invalid-uuid"
