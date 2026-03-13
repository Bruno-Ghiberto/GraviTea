"""
Shared OpenAPI schema serializers for RFC 7807 error responses.

Provides DRF serializers for documenting error responses in OpenAPI schema.
These are used by drf-spectacular for schema generation and must have
unique names to avoid component collisions.

Per spec.md FR-001 through FR-006 requirements.
"""

from rest_framework import serializers


class FieldErrorSerializer(serializers.Serializer):
    """RFC 7807 field-level validation error.

    Represents a single field validation error within a ProblemDetail response.
    Used in the 'errors' array for 400 Bad Request responses.
    """

    field = serializers.CharField(
        help_text="Field name or path using dot notation (e.g., 'items.0.quantity')"
    )
    message = serializers.CharField(help_text="Human-readable error message")
    code = serializers.CharField(
        help_text="Machine-readable error code (e.g., 'required', 'invalid')"
    )


class ProblemDetailSerializer(serializers.Serializer):
    """RFC 7807 Problem Details error response.

    Standard error response format for all 4xx and 5xx responses.
    Includes trace_id for log correlation in production debugging.
    """

    type = serializers.URLField(
        help_text="URI reference identifying the problem type category",
        default="about:blank",
    )
    title = serializers.CharField(
        max_length=100, help_text="Short, human-readable error summary"
    )
    status = serializers.IntegerField(
        help_text="HTTP status code (400-599)", min_value=400, max_value=599
    )
    detail = serializers.CharField(
        max_length=500, help_text="Human-readable explanation of this specific error"
    )
    trace_id = serializers.UUIDField(help_text="UUID v4 for log correlation")
    instance = serializers.URLField(
        required=False, help_text="URI of the specific resource that caused the error"
    )


class ValidationErrorSerializer(ProblemDetailSerializer):
    """RFC 7807 validation error response with field-level details.

    Extended ProblemDetail for 400 Bad Request responses that include
    field-level validation errors in the 'errors' array.
    """

    # Note: 'errors' shadows base class property but is intentional for RFC 7807
    errors = serializers.ListField(  # type: ignore[assignment]
        child=FieldErrorSerializer(),
        help_text="List of field-level validation errors",
        required=False,
    )


class RateLimitErrorSerializer(ProblemDetailSerializer):
    """RFC 7807 rate limit error with retry information.

    Extended ProblemDetail for 429 Too Many Requests responses
    that include retry timing information.
    """

    retry_after = serializers.IntegerField(
        help_text="Seconds until the next request attempt is allowed"
    )


class AccountLockedErrorSerializer(ProblemDetailSerializer):
    """RFC 7807 account locked error response.

    Extended ProblemDetail for account lockout scenarios
    after excessive failed authentication attempts.
    """

    account_locked = serializers.BooleanField(
        help_text="Whether the account is permanently locked", default=True
    )
    contact_support = serializers.CharField(
        help_text="Support contact information", required=False
    )
