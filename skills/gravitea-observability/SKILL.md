---
name: gravitea-observability
description: >
  Observability patterns for GRAVITEA-ERP including Prometheus metrics, OpenTelemetry tracing, business metrics, and alerting.
  Trigger: When editing apps/core/observability/, adding metrics, tracing spans, or alert rules.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Observability Skill

Patterns for Prometheus metrics, OpenTelemetry tracing, business metrics, and alerting in a multi-tenant context.

## When to Use

- Adding new Prometheus metrics (Counter, Gauge, Histogram)
- Implementing distributed tracing spans
- Recording business metrics (orders, inventory, sync)
- Creating alert rules for fiscal, sync, or security events
- Sanitizing sensitive data in observability outputs

---

## Critical Patterns

### Pattern 1: RED Metrics (Request Rate, Errors, Duration)

**Use Counter for totals, Histogram for latency, Gauge for in-progress tracking.**

```python
# apps/core/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

REGISTRY = CollectorRegistry()

# Rate: Total request count by method, endpoint, status, tenant
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "tenant_id"],
    registry=REGISTRY,
)

# Duration: Request latency with buckets for percentiles
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "tenant_id"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

# In-Progress: Current active requests
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint", "tenant_id"],
    registry=REGISTRY,
)


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
    normalized_endpoint = normalize_path(endpoint)
    sanitized_endpoint = sanitize_endpoint_label(normalized_endpoint)
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
```

---

### Pattern 2: Database Query Metrics

**Track query count and latency by operation type.**

```python
# apps/core/observability/metrics.py
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
```

---

### Pattern 3: Business Metrics

**Domain-specific metrics for orders, inventory, sync, and auth.**

```python
# apps/core/observability/business_metrics.py

# Order Metrics
orders_total = Counter(
    "gravitea_orders_total",
    "Total orders processed",
    ["tenant_id", "branch_id", "status"],
)

order_value_total = Counter(
    "gravitea_order_value_total",
    "Total order monetary value",
    ["tenant_id", "branch_id", "currency"],
)

# Inventory Metrics
inventory_movements_total = Counter(
    "gravitea_inventory_movements_total",
    "Total inventory movements",
    ["tenant_id", "branch_id", "movement_type"],
)

low_stock_alerts = Gauge(
    "gravitea_low_stock_alerts",
    "Current low stock alerts count",
    ["tenant_id", "branch_id"],
)

# Sync Metrics
sync_queue_depth = Gauge(
    "gravitea_sync_queue_depth",
    "Pending sync operations count",
    ["tenant_id", "device_id"],
)

sync_conflicts_total = Counter(
    "gravitea_sync_conflicts_total",
    "Total sync conflicts",
    ["tenant_id", "entity_type", "resolution"],
)

# Auth Metrics
auth_attempts_total = Counter(
    "gravitea_auth_attempts_total",
    "Total authentication attempts",
    ["tenant_id", "method"],
)

auth_failures_total = Counter(
    "gravitea_auth_failures_total",
    "Failed authentication attempts",
    ["tenant_id", "reason"],
)


def record_order(
    tenant_id: str,
    branch_id: str = "unknown",
    status: str = "completed",
    amount: Optional[float] = None,
    currency: str = "CRC",
) -> None:
    """
    Record an order event.

    Args:
        tenant_id: Tenant identifier
        branch_id: Branch identifier
        status: Order status (completed, cancelled, pending)
        amount: Order monetary value (optional)
        currency: Currency code (default: CRC)
    """
    try:
        orders_total.labels(
            tenant_id=tenant_id,
            branch_id=branch_id,
            status=status,
        ).inc()

        if amount is not None and amount > 0:
            order_value_total.labels(
                tenant_id=tenant_id,
                branch_id=branch_id,
                currency=currency,
            ).inc(amount)
    except Exception as e:
        logger.warning("Failed to record order metric: %s", e)
```

---

### Pattern 4: OpenTelemetry Tracing

**Create spans with context manager and auto-scrub sensitive data.**

```python
# apps/core/observability/tracing.py
from contextlib import contextmanager
from typing import Any, Generator, Optional

SENSITIVE_PATTERNS = [
    "password", "secret", "token", "api_key", "authorization",
    "credential", "private", "access_key", "refresh_token",
]


@contextmanager
def create_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    kind: Optional[Any] = None,
) -> Generator[Optional["Span"], None, None]:
    """
    Create a new span for the given operation.

    Args:
        name: Span name (e.g., "process_order", "db_query")
        attributes: Span attributes
        kind: Span kind (SpanKind.INTERNAL, SpanKind.CLIENT, etc.)

    Yields:
        Span object if tracing is enabled, None otherwise

    Example:
        with create_span("process_order", {"order_id": "123"}) as span:
            if span:
                span.set_attribute("status", "completed")
    """
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry.trace import SpanKind

    span_kind = kind or SpanKind.INTERNAL

    with tracer.start_as_current_span(name, kind=span_kind, attributes=attributes or {}) as span:
        yield span


def scrub_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """
    Scrub sensitive data from span attributes.

    Args:
        attributes: Original attributes

    Returns:
        Attributes with sensitive values redacted
    """
    scrubbed = {}
    for key, value in attributes.items():
        # Normalize key for pattern matching
        key_normalized = key.lower().replace('-', '').replace('_', '')

        # Check if any sensitive pattern appears in the normalized key
        is_sensitive = any(
            pattern.replace('_', '') in key_normalized
            for pattern in SENSITIVE_PATTERNS
        )

        if is_sensitive:
            scrubbed[key] = "[REDACTED]"
        elif key == "db.statement" and get_config().scrub_db_statements:
            scrubbed[key] = scrub_sql_values(str(value))
        else:
            scrubbed[key] = value
    return scrubbed
```

**Usage in views:**

```python
# Example: Tracing in a view
from apps.core.observability.tracing import create_span

class ProductViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        with create_span("product.create", {"tenant_id": str(request.user.tenant_id)}) as span:
            # ... create logic ...
            if span:
                span.set_attribute("product_id", str(product.id))
            return Response(serializer.data)
```

---

### Pattern 5: Alert System

**Typed alerts with rate limiting, deduplication, and handlers.**

```python
# apps/core/observability/alerts.py
from enum import Enum
from typing import Optional

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(Enum):
    FISCAL = "fiscal"
    SYNC = "sync"
    SECURITY = "security"
    SYSTEM = "system"


def fiscal_alert(
    service: str,
    operation: str,
    error: str,
    tenant_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    context: Optional[dict] = None,
    level: AlertLevel = AlertLevel.ERROR,
) -> Optional[Alert]:
    """
    Send a fiscal service failure alert (SC-021).

    Must generate alert within 1 minute of occurrence.

    Args:
        service: Fiscal service name (e.g., "afip", "arca")
        operation: Operation that failed (e.g., "invoice_emission", "cae_request")
        error: Error message/description
        tenant_id: Tenant ID
        branch_id: Branch ID if applicable
        context: Additional context (cae_request_id, retry_count, etc.)
        level: Alert severity (default: ERROR)
    """
    manager = get_alert_manager()
    full_context = {
        "service": service,
        "operation": operation,
        "error_detail": error,
        **(context or {}),
    }

    return manager.send_alert(
        alert_type=AlertType.FISCAL,
        level=level,
        message=f"Fiscal service failure: {service}/{operation} - {error}",
        source=f"fiscal.{service}",
        tenant_id=tenant_id,
        branch_id=branch_id,
        context=full_context,
    )


def security_alert(
    event_type: str,
    message: str,
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    context: Optional[dict] = None,
    level: AlertLevel = AlertLevel.WARNING,
) -> Optional[Alert]:
    """
    Send a security-related alert.

    Args:
        event_type: Security event type (e.g., "failed_login", "idor_attempt")
        message: Human-readable description
        tenant_id: Tenant ID
        user_id: User ID if applicable
        ip_address: Client IP address
        context: Additional context
        level: Alert severity
    """
    manager = get_alert_manager()
    return manager.send_alert(
        alert_type=AlertType.SECURITY,
        level=level,
        message=message,
        source=f"security.{event_type}",
        tenant_id=tenant_id,
        context={
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            **(context or {}),
        },
    )
```

---

### Pattern 6: Endpoint Path Normalization

**Collapse dynamic IDs to prevent metric cardinality explosion.**

```python
# apps/core/observability/metrics.py
import re

# Patterns to normalize dynamic path segments
PATH_NORMALIZERS = [
    # UUID patterns
    (re.compile(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I), '/{id}'),
    # Numeric IDs
    (re.compile(r'/\d+'), '/{id}'),
]

# Sensitive paths to redact completely
SENSITIVE_ENDPOINT_PATTERNS = [
    re.compile(r'.*/auth/token.*'),
    re.compile(r'.*/password.*'),
    re.compile(r'.*/credentials.*'),
]


def normalize_path(path: str) -> str:
    """
    Normalize request path by collapsing dynamic IDs.

    Examples:
        /api/v1/products/550e8400-e29b-41d4-a716-446655440000/
        → /api/v1/products/{id}/

        /api/v1/orders/12345/items/67890/
        → /api/v1/orders/{id}/items/{id}/
    """
    for pattern, replacement in PATH_NORMALIZERS:
        path = pattern.sub(replacement, path)
    return path


def sanitize_endpoint_label(endpoint: str) -> str:
    """
    Sanitize endpoint for use as metric label.

    Sensitive endpoints are replaced with generic labels.
    """
    for pattern in SENSITIVE_ENDPOINT_PATTERNS:
        if pattern.match(endpoint):
            return "/[sensitive]"
    return endpoint
```

---

## Decision Tree

```
Adding observability?
|-- Request metrics? -> Use RED pattern (Rate, Errors, Duration)
|-- Business event? -> Use domain-specific business metrics
|-- Distributed tracing? -> Use create_span() context manager
+-- Alert needed?
    |-- Fiscal failure? -> fiscal_alert()
    |-- Security event? -> security_alert()
    |-- Sync problem? -> sync_alert()
    +-- System issue? -> system_alert()

Choosing metric type?
|-- Counting events? -> Counter (always increases)
|-- Current value? -> Gauge (can go up/down)
|-- Measuring latency? -> Histogram (with buckets)

Handling sensitive data?
|-- In span attributes? -> Use scrub_attributes()
|-- In metric labels? -> Use sanitize_endpoint_label()
|-- In SQL statements? -> Enable scrub_db_statements
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: High Cardinality Labels

```python
# FORBIDDEN - Unbounded label values cause memory issues
http_requests_total.labels(
    endpoint=request.path,  # Raw path with UUIDs!
    user_id=request.user.id,  # Per-user metrics = explosion
).inc()

# CORRECT - Normalize paths, use tenant_id not user_id
http_requests_total.labels(
    endpoint=normalize_path(request.path),  # /api/v1/products/{id}/
    tenant_id=tenant_label,  # Bounded by tenant count
).inc()
```

### Anti-Pattern 2: Sensitive Data in Metrics/Traces

```python
# FORBIDDEN - Logging tokens
span.set_attribute("authorization", request.headers.get("Authorization"))
span.set_attribute("password", form_data.get("password"))

# CORRECT - Use scrub_attributes() or avoid sensitive data
attributes = scrub_attributes({
    "authorization": request.headers.get("Authorization"),
})
# Result: {"authorization": "[REDACTED]"}
```

### Anti-Pattern 3: Blocking on Observability

```python
# FORBIDDEN - Synchronous external calls in request path
def record_metric():
    requests.post("http://external-collector/metrics", json=data)  # Blocking!

# CORRECT - Use async or non-blocking approaches
def record_metric():
    # prometheus_client handles this internally
    # For custom collectors, use async/background tasks
    counter.inc()
```

### Anti-Pattern 4: Missing Tenant Context

```python
# FORBIDDEN - Metrics without tenant isolation
orders_total.labels(status="completed").inc()

# CORRECT - Always include tenant_id for business metrics
orders_total.labels(
    tenant_id=tenant_id,
    branch_id=branch_id,
    status="completed",
).inc()
```

---

## Testing Observability

```python
# tests/unit/observability/test_metrics.py
import pytest
from apps.core.observability.metrics import (
    normalize_path,
    sanitize_endpoint_label,
    record_request,
)

class TestPathNormalization:
    def test_uuid_normalized(self):
        """UUIDs are collapsed to {id}."""
        path = "/api/v1/products/550e8400-e29b-41d4-a716-446655440000/"
        assert normalize_path(path) == "/api/v1/products/{id}/"

    def test_numeric_id_normalized(self):
        """Numeric IDs are collapsed to {id}."""
        path = "/api/v1/orders/12345/"
        assert normalize_path(path) == "/api/v1/orders/{id}/"

    def test_sensitive_endpoint_sanitized(self):
        """Sensitive endpoints are redacted."""
        path = "/api/v1/auth/token/refresh/"
        assert sanitize_endpoint_label(path) == "/[sensitive]"


# tests/unit/observability/test_tracing.py
from apps.core.observability.tracing import scrub_attributes

class TestAttributeScrubbing:
    def test_password_redacted(self):
        """Password fields are redacted."""
        attrs = {"user_password": "secret123", "username": "john"}
        result = scrub_attributes(attrs)
        assert result["user_password"] == "[REDACTED]"
        assert result["username"] == "john"

    def test_authorization_redacted(self):
        """Authorization headers are redacted."""
        attrs = {"http.authorization": "Bearer xxx"}
        result = scrub_attributes(attrs)
        assert result["http.authorization"] == "[REDACTED]"
```

---

## Commands

```bash
# Run observability tests
cd backend && pytest tests/unit/observability/ -v

# Check metrics endpoint
curl http://localhost:8000/metrics/

# View Prometheus locally
docker-compose -f docker-compose.observability.yml up -d
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)

# Check tracing (Jaeger)
# http://localhost:16686

# Query example metrics
curl -s http://localhost:9090/api/v1/query \
  -d 'query=http_requests_total{status_code="200"}'
```

---

## Developer Checklist

Before submitting observability code, verify:

- [ ] Metric names follow `gravitea_` prefix for business metrics
- [ ] Labels have bounded cardinality (no raw UUIDs)
- [ ] Sensitive data scrubbed from traces and logs
- [ ] Histogram buckets match expected latency distribution
- [ ] Tenant context included in business metrics
- [ ] Alert functions use appropriate AlertLevel
- [ ] Endpoint paths normalized before labeling
- [ ] No blocking calls in metric recording
- [ ] Unit tests cover scrubbing and normalization
- [ ] Documentation updated for new metrics

---

## Resources

- **Metrics**: See `backend/apps/core/observability/metrics.py`
- **Tracing**: See `backend/apps/core/observability/tracing.py`
- **Business Metrics**: See `backend/apps/core/observability/business_metrics.py`
- **Alerts**: See `backend/apps/core/observability/alerts.py`
- **Tests**: See `backend/tests/unit/observability/`
- **Docker Stack**: See `backend/docker-compose.observability.yml`

---

*Last updated: 2026-01-20*
*Prometheus | OpenTelemetry | Grafana | Jaeger*
