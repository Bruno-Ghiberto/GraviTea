"""
Prometheus metrics collection for GRAVITEA ERP.

Implements:
- RED metrics (Request Rate, Errors, Duration)
- Cardinality-controlled labels with endpoint normalization

Note: Business metrics (orders, sync, auth, inventory) are defined in
      business_metrics.py to avoid duplication.

Usage:
    from apps.core.observability.metrics import (
        REGISTRY,
        http_requests_total,
        record_request,
    )

    # In middleware
    record_request(method="GET", endpoint="/api/v1/products/", status_code=200, tenant_id="123")
"""

from __future__ import annotations

import re
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.core import CollectorRegistry
from apps.core.observability.observability_engine import (
    normalize_path as _engine_normalize_path,
    sanitize_endpoint_label as _engine_sanitize_endpoint_label,
)

# -----------------------------------------------------------------------------
# Custom Registry (avoids default process metrics for cleaner /metrics output)
# -----------------------------------------------------------------------------

REGISTRY = CollectorRegistry()

# -----------------------------------------------------------------------------
# Path Normalization (prevents cardinality explosion)
# -----------------------------------------------------------------------------

PATH_NORMALIZERS: list[tuple[re.Pattern, str]] = [
    # UUID pattern: /550e8400-e29b-41d4-a716-446655440000/ -> /{id}/
    # Matches UUID with or without trailing slash
    (re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)", re.IGNORECASE), "/{id}"),
    # Integer ID pattern: /123 -> /{id}
    # Matches integers with or without trailing slash
    (re.compile(r"/\d+(?=/|$)"), "/{id}"),
]


def normalize_path(path: str) -> str:
    """
    Normalize URL path to prevent metric cardinality explosion.

    Examples:
        /api/v1/products/550e8400-e29b-41d4-a716-446655440000/ -> /api/v1/products/{id}/
        /api/v1/branches/123/products/ -> /api/v1/branches/{id}/products/
        /api/v1/tenants/123/branches/456/products/789 -> /api/v1/tenants/{id}/branches/{id}/products/{id}
    """
    # Strip query parameters first
    path_without_query = path.split('?')[0] if '?' in path else path

    normalized = path_without_query
    for pattern, replacement in PATH_NORMALIZERS:
        # Use re.sub with count=0 to replace ALL occurrences
        normalized = pattern.sub(replacement, normalized, count=0)
    return normalized


# -----------------------------------------------------------------------------
# Endpoint Label Sanitization (sensitive data protection for Prometheus)
# -----------------------------------------------------------------------------

# Patterns that indicate sensitive data in endpoint paths
# All replacements use neutral terms to avoid exposing sensitive keywords in metrics
SENSITIVE_ENDPOINT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Password-related endpoints -> use neutral "auth-action"
    (re.compile(r"/password[-_]?reset/?", re.IGNORECASE), "/auth-action/"),
    (re.compile(r"/change[-_]?password/?", re.IGNORECASE), "/auth-action/"),
    (re.compile(r"/reset[-_]?password/?", re.IGNORECASE), "/auth-action/"),
    (re.compile(r"/forgot[-_]?password/?", re.IGNORECASE), "/auth-action/"),
    # Token-related endpoints -> use neutral "auth"
    (re.compile(r"/token/[^/]+/?", re.IGNORECASE), "/auth/{redacted}/"),
    (re.compile(r"/token/?", re.IGNORECASE), "/auth/"),
    (re.compile(r"/refresh[-_]?token/?", re.IGNORECASE), "/auth-refresh/"),
    # API key endpoints -> use neutral "key"
    (re.compile(r"/api[-_]?key/[^/]+/?", re.IGNORECASE), "/key/{redacted}/"),
    (re.compile(r"/api[-_]?key/?", re.IGNORECASE), "/key/"),
    # Secret/credential endpoints -> fully redact
    (re.compile(r"/secret/[^/]+/?", re.IGNORECASE), "/{redacted}/"),
    (re.compile(r"/secret/?", re.IGNORECASE), "/{redacted}/"),
    (re.compile(r"/credential/[^/]+/?", re.IGNORECASE), "/{redacted}/"),
    (re.compile(r"/credential/?", re.IGNORECASE), "/{redacted}/"),
    (re.compile(r"/private[-_]?key/?", re.IGNORECASE), "/{redacted}/"),
    # Auth verification endpoints that might contain tokens
    (re.compile(r"/verify/[^/]+/?", re.IGNORECASE), "/verify/{redacted}/"),
    (re.compile(r"/activate/[^/]+/?", re.IGNORECASE), "/activate/{redacted}/"),
]


def sanitize_endpoint_label(endpoint: str) -> str:
    """
    Sanitize endpoint paths for Prometheus metrics labels.

    Removes or redacts sensitive information from endpoint paths to prevent
    exposure of tokens, passwords, and other sensitive data in metrics.

    Args:
        endpoint: The endpoint path to sanitize

    Returns:
        Sanitized endpoint path safe for Prometheus labels

    Examples:
        /api/v1/auth/password-reset/ -> /api/v1/auth/auth-action/
        /api/v1/token/abc123xyz/ -> /api/v1/auth/{redacted}/
        /api/v1/verify/some-token-here/ -> /api/v1/verify/{redacted}/
    """
    sanitized = endpoint
    for pattern, replacement in SENSITIVE_ENDPOINT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    # Final fallback: replace any remaining sensitive words with neutral terms.
    # Word boundaries (\b) prevent false matches on substrings (M-012).
    sanitized = re.sub(r'\bpassword\b', 'auth', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\bsecret\b', 'redacted', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\btoken\b', 'auth', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\bapi[_-]?key\b', 'key', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\bprivate[_-]?key\b', 'redacted', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\bcredential\b', 'redacted', sanitized, flags=re.IGNORECASE)

    return sanitized


# -----------------------------------------------------------------------------
# RED Metrics (Request Rate, Errors, Duration)
# -----------------------------------------------------------------------------

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "tenant_id"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "tenant_id"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint", "tenant_id"],
    registry=REGISTRY,
)


# -----------------------------------------------------------------------------
# Database Query Metrics
# -----------------------------------------------------------------------------

django_db_query_total = Counter(
    "django_db_query_total",
    "Total database queries",
    ["alias", "operation"],
    registry=REGISTRY,
)

django_db_query_duration_seconds = Histogram(
    "django_db_query_duration_seconds",
    "Database query latency in seconds",
    ["alias", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=REGISTRY,
)


def record_db_query(
    alias: str,
    operation: str,
    duration: float,
) -> None:
    """
    Record database query metrics.

    Args:
        alias: Database alias (e.g., "default")
        operation: Query operation type (SELECT, INSERT, UPDATE, DELETE)
        duration: Query duration in seconds
    """
    django_db_query_total.labels(alias=alias, operation=operation).inc()
    django_db_query_duration_seconds.labels(alias=alias, operation=operation).observe(duration)


# -----------------------------------------------------------------------------
# Helper Functions for RED Metrics
# -----------------------------------------------------------------------------


def record_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    tenant_id: Optional[str] = None,
) -> None:
    """
    Record HTTP request metrics.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Request path (will be normalized and sanitized)
        status_code: HTTP response status code
        duration: Request duration in seconds
        tenant_id: Tenant identifier (or "anonymous" for unauthenticated)
    """
    # First normalize (collapse IDs), then sanitize (redact sensitive paths)
    # Dispatches to Rust via observability_engine when available (SPEC-021)
    normalized_endpoint = _engine_normalize_path(endpoint)
    sanitized_endpoint = _engine_sanitize_endpoint_label(normalized_endpoint)
    tenant_label = tenant_id or "anonymous"

    http_requests_total.labels(
        method=method,
        endpoint=sanitized_endpoint,
        status_code=str(status_code),
        tenant_id=tenant_label,
    ).inc()

    http_request_duration_seconds.labels(
        method=method,
        endpoint=sanitized_endpoint,
        tenant_id=tenant_label,
    ).observe(duration)
