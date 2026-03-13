"""
RFC 7807 Problem Details response structures.

Provides dataclasses for building RFC 7807 compliant error responses.
These structures ensure consistent error formatting across all API endpoints.

Per spec.md FR-001 through FR-006 requirements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldError:
    """Field-level validation error detail.

    Represents a single validation error for a specific field in the request body.
    Used within ProblemDetail.errors array for 400 Bad Request responses.

    Attributes:
        field: Field name or path using dot notation for nested fields
               (e.g., "price", "items.0.quantity")
        message: Human-readable error message explaining the validation failure
        code: Machine-readable error code in snake_case
              (e.g., "required", "invalid", "min_value", "max_length")
    """

    field: str
    message: str
    code: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict with field, message, and code keys
        """
        return asdict(self)


@dataclass(slots=True)
class ProblemDetail:
    """RFC 7807 Problem Details response structure.

    Provides standardized error response format for all API errors.
    Includes trace_id for log correlation in production debugging.

    Example response:
        {
            "type": "https://api.gravitea.com/errors/validation-error",
            "title": "Validation Error",
            "status": 400,
            "detail": "The request body contains invalid data",
            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
            "errors": [
                {"field": "price", "message": "Must be a positive number", "code": "min_value"}
            ]
        }

    Attributes:
        type: URI identifying the error category (must start with base URI)
        title: Human-readable summary, max 100 characters
        status: HTTP status code (400-599)
        detail: Specific explanation for this occurrence, max 500 characters
        trace_id: UUID v4 for log correlation
        errors: Optional list of field-level validation errors (only for 400)
        instance: Optional URI of the specific resource that caused the error
    """

    type: str
    title: str
    status: int
    detail: str
    trace_id: str
    errors: list[FieldError] | None = None
    instance: str | None = None

    # Base URI for error types
    ERROR_TYPE_BASE = "https://api.gravitea.com/errors/"

    def __post_init__(self) -> None:
        """Validate the ProblemDetail fields after initialization."""
        # Validate type is a URI
        if not self.type.startswith(("http://", "https://")):
            raise ValueError(f"type must be a valid URI, got: {self.type}")

        # Validate status is a valid error code
        if not 400 <= self.status <= 599:
            raise ValueError(f"status must be between 400-599, got: {self.status}")

        # Validate title length
        if len(self.title) > 100:
            raise ValueError(f"title must be <= 100 characters, got: {len(self.title)}")

        # Validate detail length
        if len(self.detail) > 500:
            # Truncate detail with ellipsis instead of raising
            object.__setattr__(self, "detail", self.detail[:497] + "...")

        # Errors should only be present for 400 status
        if self.errors is not None and self.status != 400:
            raise ValueError("errors array should only be present for status 400")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response.

        Returns:
            Dict representation suitable for JSON serialization
        """
        result: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "trace_id": self.trace_id,
        }

        if self.errors is not None:
            result["errors"] = [e.to_dict() for e in self.errors]

        if self.instance is not None:
            result["instance"] = self.instance

        return result

    @classmethod
    def from_error_code(
        cls,
        error_code: str,
        status: int,
        detail: str,
        trace_id: str,
        *,
        errors: list[FieldError] | None = None,
        instance: str | None = None,
        title: str | None = None,
    ) -> ProblemDetail:
        """Create a ProblemDetail from an error code.

        This is the preferred factory method for creating ProblemDetail instances.
        The error_code is appended to the base URI to form the type field.

        Args:
            error_code: Short identifier (e.g., "validation-error", "not-found")
            status: HTTP status code
            detail: Specific error explanation
            trace_id: UUID for log correlation
            errors: Optional field-level validation errors
            instance: Optional resource URI
            title: Optional custom title (defaults to title-cased error_code)

        Returns:
            A new ProblemDetail instance
        """
        if title is None:
            # Convert "validation-error" to "Validation Error"
            title = error_code.replace("-", " ").title()

        return cls(
            type=f"{cls.ERROR_TYPE_BASE}{error_code}",
            title=title,
            status=status,
            detail=detail,
            trace_id=trace_id,
            errors=errors,
            instance=instance,
        )
