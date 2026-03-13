"""
RFC 7807 Problem Details exception handling package.

This package provides:
- RFC 7807 compliant error response formatting
- Custom exception handler for Django REST Framework
- Error type catalog with documented URIs
- Trace ID correlation for production debugging
- TenantContextError for fail-closed RLS enforcement

Per spec.md FR-001 through FR-008 requirements.
"""

from apps.core.exceptions.problem_detail import FieldError, ProblemDetail
from apps.core.exceptions.trace import TraceContext


class TenantContextError(RuntimeError):
    """Raised when PostgreSQL tenant context (RLS) cannot be set.

    This is a SECURITY-CRITICAL exception.  If SET LOCAL
    app.current_tenant_id fails, RLS policies will not be enforced
    for the current transaction.  Fail-closed: the query MUST NOT
    proceed without RLS context.
    """


__all__ = [
    "ProblemDetail",
    "FieldError",
    "TraceContext",
    "TenantContextError",
]
