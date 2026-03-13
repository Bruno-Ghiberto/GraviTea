"""
Trace context for distributed tracing and log correlation.

Provides request-scoped context for correlating logs, errors, and metrics
across the application. The trace_id is included in all RFC 7807 error responses.

Per spec.md FR-007, FR-008 requirements.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest

# Context variable for storing trace context across async boundaries
_trace_context: ContextVar[TraceContext | None] = ContextVar("trace_context", default=None)


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Request trace context for correlation.

    This dataclass holds information needed to correlate logs, errors, and
    metrics for a single request. The trace_id is a UUID v4 generated at
    request start and included in all responses and log entries.

    Attributes:
        trace_id: UUID v4, unique per request, used for log correlation
        tenant_id: Current tenant ID from JWT claims (may be None)
        branch_id: Current branch ID from JWT claims (may be None)
        user_id: Current user ID from JWT claims (may be None)
        request_path: HTTP request path (e.g., /api/v1/products/)
        request_method: HTTP method (e.g., GET, POST, PATCH)
    """

    trace_id: str
    tenant_id: str | None = None
    branch_id: str | None = None
    user_id: str | None = None
    request_path: str = ""
    request_method: str = ""

    @classmethod
    def from_request(cls, request: HttpRequest) -> TraceContext:
        """Create a TraceContext from an HTTP request.

        Extracts tenant_id, branch_id, and user_id from the request's
        authenticated user if available. Generates a new trace_id.

        Args:
            request: The Django HTTP request object

        Returns:
            A new TraceContext instance populated from the request
        """
        # Check for existing trace ID from header (for distributed tracing)
        trace_id = request.META.get("HTTP_X_TRACE_ID")
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # Extract user context if authenticated
        tenant_id = None
        branch_id = None
        user_id = None

        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id) if hasattr(request.user, "id") else None
            tenant_id = (
                str(request.user.tenant_id)
                if hasattr(request.user, "tenant_id") and request.user.tenant_id
                else None
            )
            branch_id = (
                str(request.user.default_branch_id)
                if hasattr(request.user, "default_branch_id") and request.user.default_branch_id
                else None
            )

        return cls(
            trace_id=trace_id,
            tenant_id=tenant_id,
            branch_id=branch_id,
            user_id=user_id,
            request_path=request.path,
            request_method=request.method or "",
        )

    def to_log_extra(self) -> dict[str, str | None]:
        """Return a dictionary suitable for logging extra fields.

        Returns:
            Dict with trace context fields for structured logging
        """
        return {
            "trace_id": self.trace_id,
            "tenant_id": self.tenant_id,
            "branch_id": self.branch_id,
            "user_id": self.user_id,
            "request_path": self.request_path,
            "request_method": self.request_method,
        }


def set_trace_context(ctx: TraceContext) -> None:
    """Set the current trace context for this request.

    Args:
        ctx: The TraceContext to set as current
    """
    _trace_context.set(ctx)


def get_trace_context() -> TraceContext | None:
    """Get the current trace context.

    Returns:
        The current TraceContext or None if not set
    """
    return _trace_context.get()


def clear_trace_context() -> None:
    """Clear the current trace context."""
    _trace_context.set(None)


def get_trace_id() -> str:
    """Get the current trace ID, generating one if not set.

    This is a convenience function for cases where you need a trace_id
    but may not have a full TraceContext available.

    Returns:
        The current trace_id or a newly generated UUID v4
    """
    ctx = get_trace_context()
    if ctx:
        return ctx.trace_id
    return str(uuid.uuid4())
