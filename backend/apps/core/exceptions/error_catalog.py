"""
Error catalog with documented type URIs.

Defines all standard error types used across the API with their
corresponding HTTP status codes and default messages.

Per spec.md FR-003, FR-004 requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


# Base URI for all error types
ERROR_TYPE_BASE: Final[str] = "https://api.gravitea.com/errors/"


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    """Definition of a standard error type.

    Attributes:
        code: Short identifier (e.g., "validation-error")
        title: Human-readable title (e.g., "Validation Error")
        status: Default HTTP status code
        description: Documentation description of when this error occurs
    """

    code: str
    title: str
    status: int
    description: str

    @property
    def type_uri(self) -> str:
        """Get the full type URI for this error."""
        return f"{ERROR_TYPE_BASE}{self.code}"


class ErrorCatalog(Enum):
    """Catalog of all standard API error types.

    Usage:
        error = ErrorCatalog.VALIDATION_ERROR
        print(error.value.type_uri)  # https://api.gravitea.com/errors/validation-error
        print(error.value.status)     # 400
    """

    # 400 Bad Request errors
    VALIDATION_ERROR = ErrorDefinition(
        code="validation-error",
        title="Validation Error",
        status=400,
        description="The request body contains invalid data. Check the 'errors' array for field-specific details.",
    )

    BAD_REQUEST = ErrorDefinition(
        code="bad-request",
        title="Bad Request",
        status=400,
        description="The request could not be understood or was missing required parameters.",
    )

    INVALID_JSON = ErrorDefinition(
        code="invalid-json",
        title="Invalid JSON",
        status=400,
        description="The request body is not valid JSON.",
    )

    # 401 Unauthorized errors
    UNAUTHORIZED = ErrorDefinition(
        code="unauthorized",
        title="Unauthorized",
        status=401,
        description="Authentication is required to access this resource.",
    )

    INVALID_CREDENTIALS = ErrorDefinition(
        code="invalid-credentials",
        title="Invalid Credentials",
        status=401,
        description="The provided email or password is incorrect.",
    )

    TOKEN_EXPIRED = ErrorDefinition(
        code="token-expired",
        title="Token Expired",
        status=401,
        description="The access token has expired. Obtain a new token using the refresh endpoint.",
    )

    TOKEN_INVALID = ErrorDefinition(
        code="token-invalid",
        title="Invalid Token",
        status=401,
        description="The provided token is malformed or has been tampered with.",
    )

    # 403 Forbidden errors
    FORBIDDEN = ErrorDefinition(
        code="forbidden",
        title="Forbidden",
        status=403,
        description="You do not have permission to perform this action.",
    )

    INSUFFICIENT_PERMISSIONS = ErrorDefinition(
        code="insufficient-permissions",
        title="Insufficient Permissions",
        status=403,
        description="Your role does not have the required permissions for this operation.",
    )

    # 404 Not Found errors
    NOT_FOUND = ErrorDefinition(
        code="not-found",
        title="Not Found",
        status=404,
        description="The requested resource does not exist or you do not have access to it.",
    )

    RESOURCE_NOT_FOUND = ErrorDefinition(
        code="resource-not-found",
        title="Resource Not Found",
        status=404,
        description="The specified resource could not be found.",
    )

    # 405 Method Not Allowed
    METHOD_NOT_ALLOWED = ErrorDefinition(
        code="method-not-allowed",
        title="Method Not Allowed",
        status=405,
        description="The HTTP method is not allowed for this endpoint.",
    )

    # 409 Conflict errors
    CONFLICT = ErrorDefinition(
        code="conflict",
        title="Conflict",
        status=409,
        description="The request conflicts with the current state of the resource.",
    )

    DUPLICATE_RESOURCE = ErrorDefinition(
        code="duplicate-resource",
        title="Duplicate Resource",
        status=409,
        description="A resource with the same unique identifier already exists.",
    )

    CONCURRENT_MODIFICATION = ErrorDefinition(
        code="concurrent-modification",
        title="Concurrent Modification",
        status=409,
        description="The resource was modified by another request. Please retry with the latest version.",
    )

    # 422 Unprocessable Entity
    UNPROCESSABLE_ENTITY = ErrorDefinition(
        code="unprocessable-entity",
        title="Unprocessable Entity",
        status=422,
        description="The request was well-formed but contains semantic errors.",
    )

    BUSINESS_RULE_VIOLATION = ErrorDefinition(
        code="business-rule-violation",
        title="Business Rule Violation",
        status=422,
        description="The request violates a business rule.",
    )

    INSUFFICIENT_STOCK = ErrorDefinition(
        code="insufficient-stock",
        title="Insufficient Stock",
        status=422,
        description="There is not enough stock to complete this operation.",
    )

    # 429 Rate Limit errors
    RATE_LIMIT_EXCEEDED = ErrorDefinition(
        code="rate-limit-exceeded",
        title="Rate Limit Exceeded",
        status=429,
        description="Too many requests. Please wait before making another request.",
    )

    # 500 Internal Server errors
    INTERNAL_ERROR = ErrorDefinition(
        code="internal-error",
        title="Internal Server Error",
        status=500,
        description="An unexpected error occurred. Please try again or contact support if the issue persists.",
    )

    DATABASE_ERROR = ErrorDefinition(
        code="database-error",
        title="Database Error",
        status=500,
        description="A database error occurred. Please try again later.",
    )

    # 502 Bad Gateway
    BAD_GATEWAY = ErrorDefinition(
        code="bad-gateway",
        title="Bad Gateway",
        status=502,
        description="An upstream service returned an invalid response.",
    )

    # 503 Service Unavailable
    SERVICE_UNAVAILABLE = ErrorDefinition(
        code="service-unavailable",
        title="Service Unavailable",
        status=503,
        description="The service is temporarily unavailable. Please try again later.",
    )

    # 504 Gateway Timeout
    GATEWAY_TIMEOUT = ErrorDefinition(
        code="gateway-timeout",
        title="Gateway Timeout",
        status=504,
        description="An upstream service did not respond in time.",
    )


def get_error_by_code(code: str) -> ErrorDefinition | None:
    """Look up an error definition by its code.

    Args:
        code: The error code (e.g., "validation-error")

    Returns:
        The ErrorDefinition if found, None otherwise
    """
    for error in ErrorCatalog:
        if error.value.code == code:
            return error.value
    return None


def get_error_by_status(status: int) -> ErrorDefinition:
    """Get a default error definition for an HTTP status code.

    Returns the most generic error for the given status code.

    Args:
        status: HTTP status code

    Returns:
        A matching ErrorDefinition
    """
    status_to_error: dict[int, ErrorCatalog] = {
        400: ErrorCatalog.BAD_REQUEST,
        401: ErrorCatalog.UNAUTHORIZED,
        403: ErrorCatalog.FORBIDDEN,
        404: ErrorCatalog.NOT_FOUND,
        405: ErrorCatalog.METHOD_NOT_ALLOWED,
        409: ErrorCatalog.CONFLICT,
        422: ErrorCatalog.UNPROCESSABLE_ENTITY,
        429: ErrorCatalog.RATE_LIMIT_EXCEEDED,
        500: ErrorCatalog.INTERNAL_ERROR,
        502: ErrorCatalog.BAD_GATEWAY,
        503: ErrorCatalog.SERVICE_UNAVAILABLE,
        504: ErrorCatalog.GATEWAY_TIMEOUT,
    }

    error_enum = status_to_error.get(status, ErrorCatalog.INTERNAL_ERROR)
    return error_enum.value
