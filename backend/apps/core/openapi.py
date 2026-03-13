"""
OpenAPI schema postprocessing hooks for GRAVITEA ERP.

Ensures all error responses conform to RFC 7807 Problem Details format.
"""

from __future__ import annotations

from typing import Any


# Error type URI base
ERROR_TYPE_BASE = "https://api.gravitea.com/errors"

# Error type mappings
ERROR_TYPES = {
    400: "validation-error",
    401: "authentication-required",
    403: "permission-denied",
    404: "not-found",
    405: "method-not-allowed",
    409: "conflict",
    429: "rate-limit-exceeded",
    500: "internal-error",
    503: "service-unavailable",
}

# Error titles
ERROR_TITLES = {
    400: "Validation Error",
    401: "Authentication Required",
    403: "Permission Denied",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    429: "Rate Limit Exceeded",
    500: "Internal Server Error",
    503: "Service Unavailable",
}

# Error detail examples
ERROR_DETAILS = {
    400: "One or more fields contain invalid values",
    401: "Authentication credentials were not provided or are invalid",
    403: "You do not have permission to perform this action",
    404: "The requested resource was not found",
    405: "Method not allowed for this endpoint",
    409: "The request conflicts with the current state of the resource",
    429: "Too many requests. Please try again later",
    500: "An unexpected error occurred while processing your request",
    503: "The service is temporarily unavailable. Please try again later",
}


def postprocess_schema(result: dict[str, Any], generator, request, public) -> dict[str, Any]:
    """
    Postprocess the OpenAPI schema to add RFC 7807 error schemas.

    This hook is called by drf-spectacular after schema generation.
    It ensures all error responses conform to RFC 7807 Problem Details format.

    Args:
        result: The generated OpenAPI schema dictionary
        generator: The schema generator instance
        request: The HTTP request (if available)
        public: Boolean indicating if this is a public schema

    Returns:
        The modified OpenAPI schema with RFC 7807 error responses
    """
    # Add error schemas to components
    _add_error_schemas(result)

    # Update error responses throughout the schema
    _update_error_responses(result)

    return result


def _add_error_schemas(schema: dict[str, Any]) -> None:
    """
    Add RFC 7807 ProblemDetail and FieldError schemas.

    Args:
        schema: The OpenAPI schema dictionary to modify
    """
    # Ensure components and schemas exist
    if "components" not in schema:
        schema["components"] = {}
    if "schemas" not in schema["components"]:
        schema["components"]["schemas"] = {}

    schemas = schema["components"]["schemas"]

    # Add FieldError schema for validation error details
    schemas["FieldError"] = {
        "type": "object",
        "required": ["field", "message", "code"],
        "properties": {
            "field": {
                "type": "string",
                "description": "Field name that caused the error",
                "example": "email",
            },
            "message": {
                "type": "string",
                "description": "Human-readable error message",
                "example": "Enter a valid email address.",
            },
            "code": {
                "type": "string",
                "description": "Machine-readable error code",
                "example": "invalid",
            },
        },
        "description": "Field-level validation error details",
    }

    # Add ProblemDetail schema for general errors
    schemas["ProblemDetail"] = {
        "type": "object",
        "required": ["type", "title", "status", "detail", "trace_id"],
        "properties": {
            "type": {
                "type": "string",
                "format": "uri",
                "description": "URI identifying the error type category",
                "example": f"{ERROR_TYPE_BASE}/not-found",
            },
            "title": {
                "type": "string",
                "description": "Human-readable error title",
                "example": "Not Found",
            },
            "status": {
                "type": "integer",
                "description": "HTTP status code",
                "example": 404,
            },
            "detail": {
                "type": "string",
                "description": "Detailed explanation of the error",
                "example": "The requested resource was not found",
            },
            "trace_id": {
                "type": "string",
                "format": "uuid",
                "description": "Unique request identifier for log correlation",
                "example": "550e8400-e29b-41d4-a716-446655440000",
            },
        },
        "description": "RFC 7807 Problem Details for HTTP APIs",
    }

    # Add ValidationError schema for 400 responses
    schemas["ValidationError"] = {
        "allOf": [
            {"$ref": "#/components/schemas/ProblemDetail"},
            {
                "type": "object",
                "properties": {
                    "errors": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/FieldError"},
                        "description": "Field-level validation error details",
                        "example": [
                            {
                                "field": "email",
                                "message": "Enter a valid email address.",
                                "code": "invalid",
                            },
                            {
                                "field": "username",
                                "message": "This field is required.",
                                "code": "required",
                            },
                        ],
                    },
                },
            },
        ],
        "description": "Validation error response with field-level details",
    }


def _update_error_responses(schema: dict[str, Any]) -> None:
    """
    Update all error responses to reference RFC 7807 schemas.

    Iterates through all paths and operations, replacing default error
    responses with RFC 7807-compliant schemas.

    Args:
        schema: The OpenAPI schema dictionary to modify
    """
    if "paths" not in schema:
        return

    for path_item in schema["paths"].values():
        for operation in path_item.values():
            # Skip if not an operation (e.g., parameters, summary)
            if not isinstance(operation, dict) or "responses" not in operation:
                continue

            responses = operation["responses"]

            # Update each error response
            for status_code_str, response in list(responses.items()):
                try:
                    status_code = int(status_code_str)
                except (ValueError, TypeError):
                    continue

                # Only update error responses (4xx and 5xx)
                if status_code < 400:
                    continue

                # Get error type and details
                error_type = ERROR_TYPES.get(status_code)
                error_title = ERROR_TITLES.get(status_code, "Error")
                error_detail = ERROR_DETAILS.get(status_code, "An error occurred")

                if not error_type:
                    continue

                # Build the error response
                error_uri = f"{ERROR_TYPE_BASE}/{error_type}"

                # Use ValidationError for 400, ProblemDetail for others
                schema_ref = (
                    "#/components/schemas/ValidationError"
                    if status_code == 400
                    else "#/components/schemas/ProblemDetail"
                )

                # Create example based on status code
                example = {
                    "type": error_uri,
                    "title": error_title,
                    "status": status_code,
                    "detail": error_detail,
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                }

                # Add errors array for validation errors
                if status_code == 400:
                    example["errors"] = [
                        {
                            "field": "email",
                            "message": "Enter a valid email address.",
                            "code": "invalid",
                        }
                    ]

                # Update the response
                responses[status_code_str] = {
                    "description": error_title,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": schema_ref},
                            "example": example,
                        }
                    },
                }
