"""
RFC 7807 exception handler for Django REST Framework.

Converts all DRF exceptions to RFC 7807 Problem Details format with
trace_id correlation for production debugging.

Per spec.md FR-001 through FR-008 requirements.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.exceptions.error_catalog import ErrorCatalog, get_error_by_status
from apps.core.exceptions.problem_detail import FieldError, ProblemDetail
from apps.core.exceptions.trace import get_trace_id

if TYPE_CHECKING:
    from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _extract_field_errors(detail: Any, prefix: str = "") -> list[FieldError]:
    """Extract field-level errors from DRF validation error detail.

    Handles nested validation errors using dot notation for field names.
    DRF produces validation errors in multiple formats depending on the
    serializer structure and validation type, so this function handles:

    1. dict format: {"field": ["error1", "error2"]} - most common
    2. nested dict: {"parent": {"child": ["error"]}} - nested serializers
    3. list format: ["error1", "error2"] - non-field errors
    4. single value: "error" - simple error messages

    The function recursively processes nested structures, building
    dot-notation field paths (e.g., "address.street.number").

    Args:
        detail: The error detail from DRF ValidationError
        prefix: Current field path prefix for nested fields

    Returns:
        List of FieldError instances
    """
    errors: list[FieldError] = []

    # CASE 1: Dict of field -> errors (most common DRF pattern)
    # Example: {"email": ["Invalid email"], "password": ["Too short"]}
    if isinstance(detail, dict):
        for field_name, field_errors in detail.items():
            # Build dot-notation path: "parent.child.field"
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            # Field errors are usually a list (DRF default)
            if isinstance(field_errors, list):
                for error in field_errors:
                    if isinstance(error, dict):
                        # Nested object validation error - recurse deeper
                        # Example: {"items": [{"name": ["required"]}]}
                        errors.extend(_extract_field_errors(error, field_path))
                    elif hasattr(error, "code"):
                        # DRF ErrorDetail object has .code attribute
                        # This preserves machine-readable codes like "required", "invalid"
                        errors.append(
                            FieldError(
                                field=field_path,
                                message=str(error),
                                code=error.code or "invalid",
                            )
                        )
                    else:
                        # Plain string error (fallback)
                        errors.append(
                            FieldError(
                                field=field_path,
                                message=str(error),
                                code="invalid",
                            )
                        )

            # Nested serializer validation error (recurse)
            # Example: {"address": {"city": ["required"]}}
            elif isinstance(field_errors, dict):
                errors.extend(_extract_field_errors(field_errors, field_path))

            # Single error value (uncommon but valid)
            else:
                code = getattr(field_errors, "code", "invalid") or "invalid"
                errors.append(
                    FieldError(
                        field=field_path,
                        message=str(field_errors),
                        code=code,
                    )
                )

    # CASE 2: List of errors (non-field errors or list serializer)
    # Example: ["Password mismatch"] or ListSerializer errors
    elif isinstance(detail, list):
        for idx, error in enumerate(detail):
            if isinstance(error, dict):
                # ListSerializer index-based errors: [{"name": ["required"]}]
                # Produces paths like "[0].name", "[1].name"
                index_path = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
                errors.extend(_extract_field_errors(error, index_path))
            else:
                # Non-field error - use "non_field_errors" as RFC 7807 field name
                code = getattr(error, "code", "invalid") or "invalid"
                errors.append(
                    FieldError(
                        field=prefix or "non_field_errors",
                        message=str(error),
                        code=code,
                    )
                )

    # CASE 3: Single error value (edge case)
    else:
        code = getattr(detail, "code", "invalid") or "invalid"
        errors.append(
            FieldError(
                field=prefix or "non_field_errors",
                message=str(detail),
                code=code,
            )
        )

    return errors


def _get_error_info(exc: Exception) -> tuple[str, str, int]:
    """Determine the error code, title, and status for an exception.

    Args:
        exc: The exception being handled

    Returns:
        Tuple of (error_code, title, status_code)
    """
    # Map exception types to error catalog entries
    exception_mapping: dict[type, ErrorCatalog] = {
        ValidationError: ErrorCatalog.VALIDATION_ERROR,
        ParseError: ErrorCatalog.INVALID_JSON,
        NotAuthenticated: ErrorCatalog.UNAUTHORIZED,
        AuthenticationFailed: ErrorCatalog.INVALID_CREDENTIALS,
        DRFPermissionDenied: ErrorCatalog.FORBIDDEN,
        PermissionDenied: ErrorCatalog.FORBIDDEN,
        NotFound: ErrorCatalog.NOT_FOUND,
        Http404: ErrorCatalog.NOT_FOUND,
        MethodNotAllowed: ErrorCatalog.METHOD_NOT_ALLOWED,
        Throttled: ErrorCatalog.RATE_LIMIT_EXCEEDED,
    }

    # Check for specific exception types
    for exc_type, error_enum in exception_mapping.items():
        if isinstance(exc, exc_type):
            error_def = error_enum.value
            return error_def.code, error_def.title, error_def.status

    # Handle generic APIException
    if isinstance(exc, APIException):
        status_code = exc.status_code
        error_def = get_error_by_status(status_code)
        return error_def.code, error_def.title, status_code

    # Default to internal error for unknown exceptions
    error_def = ErrorCatalog.INTERNAL_ERROR.value
    return error_def.code, error_def.title, error_def.status


def _get_detail_message(exc: Exception, is_debug: bool) -> str:
    """Generate the detail message for an exception.

    Args:
        exc: The exception being handled
        is_debug: Whether DEBUG mode is enabled

    Returns:
        The detail message (safe for production)
    """
    if isinstance(exc, ValidationError):
        return "The request body contains invalid data. See 'errors' for details."

    if isinstance(exc, NotAuthenticated):
        return "Authentication credentials were not provided."

    if isinstance(exc, AuthenticationFailed):
        # Get specific message from exception
        detail = getattr(exc, "detail", None)
        if detail:
            if isinstance(detail, dict):
                return str(detail.get("detail", "Authentication failed."))
            return str(detail)
        return "Authentication failed."

    if isinstance(exc, Throttled):
        wait = getattr(exc, "wait", None)
        if wait:
            return f"Request was throttled. Expected available in {int(wait)} seconds."
        return "Request was throttled."

    if isinstance(exc, APIException):
        detail = getattr(exc, "detail", None)
        if detail:
            if isinstance(detail, dict):
                return str(detail.get("detail", str(exc)))
            if isinstance(detail, list):
                return "; ".join(str(d) for d in detail)
            return str(detail)

    if isinstance(exc, (NotFound, Http404)):
        return "The requested resource does not exist."

    if isinstance(exc, (PermissionDenied, DRFPermissionDenied)):
        return "You do not have permission to perform this action."

    # For non-API exceptions in debug mode, include the message
    if is_debug:
        return str(exc) or "An unexpected error occurred."

    # In production, don't leak internal error details
    return "An unexpected error occurred. Please try again or contact support."


def problem_detail_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    """Custom exception handler that converts all errors to RFC 7807 format.

    This is the main entry point for exception handling in the API.
    It transforms any exception into a standardized RFC 7807 Problem Details
    response format, ensuring:

    - Consistent error structure across all endpoints
    - trace_id correlation for production debugging
    - Field-level validation errors for 400 responses
    - Production-safe error messages (no stack traces leaked)
    - Proper logging with severity-based log levels

    Flow:
        Exception → Error Classification → ProblemDetail → Response

    Args:
        exc: The exception that was raised
        context: DRF context dict with view, args, kwargs, request

    Returns:
        Response object with RFC 7807 format, or None to use default handling
    """
    # STEP 1: Get trace ID from request context (set by TraceMiddleware)
    # This ID correlates the error response with server-side logs
    trace_id = get_trace_id()

    # STEP 2: Let DRF process standard exceptions first
    # This ensures HTTP exceptions are converted to DRF-style exceptions
    response = drf_exception_handler(exc, context)

    # STEP 3: Extract request context for logging and error response
    request = context.get("request")
    view: APIView | None = context.get("view")

    # STEP 4: Classify the exception and get error metadata
    # Maps exception type to error code, title, and HTTP status
    error_code, title, status_code = _get_error_info(exc)

    # STEP 5: Generate detail message appropriate for production
    # In DEBUG mode: includes exception message
    # In production: sanitized message (no internal details leaked)
    is_debug = getattr(settings, "DEBUG", False)
    detail_message = _get_detail_message(exc, is_debug)

    # STEP 6: Extract field-level errors for validation failures
    # Only ValidationError exceptions have field-level error details
    # These populate the RFC 7807 'errors' array for 400 responses
    field_errors: list[FieldError] | None = None
    if isinstance(exc, ValidationError) and hasattr(exc, "detail"):
        field_errors = _extract_field_errors(exc.detail)

    # STEP 7: Capture the request path as the RFC 7807 'instance' field
    # This identifies which specific resource caused the error
    instance: str | None = None
    if request:
        instance = request.path

    # STEP 8: Construct the RFC 7807 ProblemDetail response object
    # This dataclass validates and formats the error structure
    problem = ProblemDetail.from_error_code(
        error_code=error_code,
        status=status_code,
        detail=detail_message,
        trace_id=trace_id,
        errors=field_errors,
        instance=instance,
        title=title,
    )

    # STEP 9: Log the error with full trace context
    # This enables searching logs by trace_id to find related entries
    log_extra = {
        "trace_id": trace_id,
        "error_code": error_code,
        "status_code": status_code,
        "request_path": request.path if request else None,
        "request_method": request.method if request else None,
        "view_name": view.__class__.__name__ if view else None,
    }

    # Log severity depends on error class:
    # - 5xx errors: ERROR level with full stack trace (server bugs)
    # - 4xx errors: WARNING level, no stack trace (client mistakes)
    if status_code >= 500:
        logger.error(
            "Server error: %s",
            detail_message,
            exc_info=exc,  # Include stack trace for debugging
            extra=log_extra,
        )
    elif status_code >= 400:
        logger.warning(
            "Client error: %s",
            detail_message,
            extra=log_extra,
        )

    # STEP 10: Return RFC 7807 response with proper Content-Type
    # application/problem+json signals RFC 7807 format to clients
    response = Response(
        data=problem.to_dict(),
        status=status_code,
        content_type="application/problem+json",
    )

    return response
