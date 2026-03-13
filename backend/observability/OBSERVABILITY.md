# GRAVITEA-ERP Observability Infrastructure

## Overview

This document describes the production-grade observability infrastructure for GRAVITEA-ERP, providing comprehensive monitoring, metrics, tracing, and alerting capabilities for the multi-tenant ERP system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GRAVITEA Backend                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Django    │  │   Sync      │  │   Auth      │             │
│  │   Views     │  │   Service   │  │   Service   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌──────────────────────────────────────────────────┐          │
│  │              Observability Layer                  │          │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │          │
│  │  │  Metrics   │ │  Tracing   │ │  Logging   │   │          │
│  │  │ Prometheus │ │OpenTelemetry│ │ Structured │   │          │
│  │  └────────────┘ └────────────┘ └────────────┘   │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐     ┌─────────────────┐    ┌──────────────┐
│ Prometheus  │     │ Jaeger/Zipkin   │    │  Log Aggr    │
│   Server    │     │ Trace Collector │    │  (ELK/Loki)  │
└─────────────┘     └─────────────────┘    └──────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│            Grafana                   │
│  ┌──────────┐ ┌──────────┐         │
│  │Overview  │ │ Business │         │
│  │Dashboard │ │ Metrics  │         │
│  └──────────┘ └──────────┘         │
│  ┌──────────┐ ┌──────────┐         │
│  │ System   │ │   SLO    │         │
│  │ Metrics  │ │ Tracking │         │
│  └──────────┘ └──────────┘         │
└─────────────────────────────────────┘
```

## Components

### 1. Prometheus Metrics (`/metrics`)

Production-ready Prometheus metrics endpoint with multi-tenant labeling.

**Endpoint**: `GET /metrics`

**Authentication**: Optional (configurable via `METRICS_REQUIRE_AUTH`)

#### System Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `db_query_total` | Counter | operation, table | Database operations |
| `db_query_duration_seconds` | Histogram | operation | Query latency |
| `process_memory_bytes` | Gauge | - | Process memory usage |
| `process_cpu_seconds_total` | Counter | - | CPU usage |

#### Business Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `gravitea_orders_total` | Counter | tenant_id, branch_id, status | Order count by status |
| `gravitea_inventory_movements_total` | Counter | tenant_id, branch_id, operation, product_type | Inventory movements |
| `gravitea_sync_operations_total` | Counter | tenant_id, operation_type, status | Sync operations |
| `gravitea_sync_queue_depth` | Gauge | tenant_id | Pending sync operations |
| `gravitea_sync_lag_seconds` | Gauge | tenant_id | Sync lag time |
| `gravitea_auth_attempts_total` | Counter | tenant_id, method | Auth attempts |
| `gravitea_auth_successes_total` | Counter | tenant_id, method | Successful auths |
| `gravitea_auth_failures_total` | Counter | tenant_id, reason | Failed auths |

### 2. Distributed Tracing

OpenTelemetry-based distributed tracing with trace correlation.

#### Configuration

```python
# settings/base.py
OTEL_SERVICE_NAME = "gravitea-backend"
OTEL_EXPORTER_OTLP_ENDPOINT = env("OTEL_EXPORTER_OTLP_ENDPOINT", default="http://jaeger:4317")
OTEL_TRACE_SAMPLE_RATE = env.float("OTEL_TRACE_SAMPLE_RATE", default=0.1)
```

#### Trace Propagation Headers

- `X-Trace-ID`: Trace identifier
- `X-Span-ID`: Current span identifier
- `X-Request-ID`: Request correlation ID
- `traceparent`: W3C trace context (standard)

#### Usage in Views

```python
from apps.core.middleware.trace_middleware import get_current_trace_context

class MyView(APIView):
    def get(self, request):
        trace_ctx = get_current_trace_context()
        logger.info("Processing request", extra={
            "trace_id": trace_ctx.get("trace_id"),
            "span_id": trace_ctx.get("span_id"),
        })
```

### 3. Structured Logging

JSON-formatted structured logging with trace correlation and multi-tenant context.

#### Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "sync",
  "message": "Sync push completed",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "request_id": "req-789",
  "tenant_id": "tenant-001",
  "user_id": "user-123",
  "extra": {
    "device_id": "pos-001",
    "operations_count": 15,
    "duration_ms": 234.5
  }
}
```

#### Sync Logger

Specialized logger for sync operations:

```python
from apps.sync.logging import SyncLogger

# Push operations
SyncLogger.log_sync_push_start(tenant_id, device_id, operation_count, ...)
SyncLogger.log_sync_push_complete(tenant_id, device_id, operations_count, ...)
SyncLogger.log_sync_push_failed(tenant_id, device_id, error, ...)

# Pull operations
SyncLogger.log_sync_pull_start(tenant_id, device_id, since_timestamp, ...)
SyncLogger.log_sync_pull_complete(tenant_id, device_id, changes_count, ...)
SyncLogger.log_sync_pull_failed(tenant_id, device_id, error, ...)

# Individual operations
SyncLogger.log_operation_applied(operation_id, entity_type, operation_type, ...)
SyncLogger.log_operation_failed(operation_id, entity_type, error, ...)
SyncLogger.log_operation_skipped(operation_id, entity_type, reason, ...)
SyncLogger.log_conflict_detected(operation_id, entity_type, server_version, ...)
```

### 4. Alert Rules

Pre-configured Prometheus alert rules in `observability/alerts/`.

#### Critical Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighErrorRate` | Error rate > 5% for 5m | critical |
| `HighLatency` | P99 latency > 1s for 5m | critical |
| `ServiceDown` | No requests for 5m | critical |

#### Warning Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| `SyncQueueGrowing` | Queue depth > 1000 | warning |
| `HighSyncLag` | Sync lag > 5m | warning |
| `AuthFailureSpike` | Auth failures > 50/min | warning |

### 5. Health Endpoints

#### Liveness Probe
```
GET /api/v1/health/live/
Response: {"status": "ok"}
```

#### Readiness Probe
```
GET /api/v1/health/ready/
Response: {"status": "ok", "checks": {"database": "ok", "cache": "ok"}}
```

## Grafana Dashboards

Pre-built dashboard templates in `observability/dashboards/`:

| Dashboard | UID | Description |
|-----------|-----|-------------|
| Overview | `gravitea-overview` | System health summary |
| System Metrics | `gravitea-system` | Detailed system performance |
| Business Metrics | `gravitea-business-metrics` | Orders, inventory, sync, auth |
| SLO Tracking | `gravitea-slo` | Service level objectives |

### Dashboard Variables

- `$datasource`: Prometheus data source
- `$tenant`: Multi-select tenant filter (business metrics)
- `$slo_window`: SLO calculation window (1h, 6h, 24h, 7d, 30d)

### Import Instructions

1. Navigate to Grafana > Dashboards > Import
2. Upload JSON file or paste contents
3. Select Prometheus data source
4. Click Import

## Configuration Reference

### Environment Variables

```bash
# Metrics
METRICS_REQUIRE_AUTH=false
METRICS_ALLOWED_IPS=10.0.0.0/8,172.16.0.0/12

# Tracing
OTEL_SERVICE_NAME=gravitea-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_TRACE_SAMPLE_RATE=0.1
OTEL_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_INCLUDE_TRACE=true
```

### Django Settings

```python
# settings/base.py

INSTALLED_APPS = [
    ...
    'apps.core.health',
    'apps.core.observability',
]

MIDDLEWARE = [
    'apps.core.middleware.trace_middleware.TraceMiddleware',
    ...
]

LOGGING = {
    'version': 1,
    'formatters': {
        'json': {
            '()': 'apps.core.logging.formatters.StructuredJSONFormatter',
        },
    },
    ...
}
```

## Integration Examples

### Recording Business Metrics

```python
from apps.core.observability.business_metrics import (
    record_order,
    record_inventory_movement,
    record_sync_operation,
)

# Record an order
record_order(
    tenant_id="tenant-001",
    branch_id="branch-001",
    status="completed"
)

# Record inventory movement
record_inventory_movement(
    tenant_id="tenant-001",
    branch_id="branch-001",
    operation="IN",
    product_type="Tea",
    quantity=100
)

# Record sync operation
record_sync_operation(
    tenant_id="tenant-001",
    operation_type="push",
    status="success"
)
```

### Adding Custom Metrics

```python
from prometheus_client import Counter, Histogram

# Define metrics
my_counter = Counter(
    'gravitea_custom_total',
    'Custom metric description',
    ['tenant_id', 'label2']
)

my_histogram = Histogram(
    'gravitea_custom_duration_seconds',
    'Custom duration metric',
    ['tenant_id'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Use metrics
my_counter.labels(tenant_id="t1", label2="value").inc()

with my_histogram.labels(tenant_id="t1").time():
    do_operation()
```

### Structured Logging

```python
import logging
from apps.core.middleware.trace_middleware import get_current_trace_context

logger = logging.getLogger("myapp")

def my_function(tenant_id, user_id):
    trace_ctx = get_current_trace_context()

    logger.info(
        "Processing operation",
        extra={
            "trace_id": trace_ctx.get("trace_id"),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "operation": "my_operation",
        }
    )
```

## SLO Definitions

| SLO | Target | Measurement |
|-----|--------|-------------|
| Availability | 99.9% | `1 - (5xx errors / total requests)` |
| Latency | P99 < 500ms | `histogram_quantile(0.99, http_request_duration_seconds)` |
| Sync Lag | < 60s | `max(gravitea_sync_lag_seconds)` |
| Sync Success | > 99% | `sync_success / sync_total` |

### Error Budget

For 99.9% availability over 30 days:
- Total minutes: 43,200
- Allowed downtime: 43.2 minutes
- Error budget: 0.1% of requests can fail

## Troubleshooting

### Metrics Not Appearing

1. Verify prometheus_client is installed
2. Check `/metrics` returns data
3. Verify Prometheus scrape config targets the correct URL
4. Check for firewall/network issues

### Traces Missing

1. Verify OTEL_ENABLED=true
2. Check OTEL_EXPORTER_OTLP_ENDPOINT is reachable
3. Verify trace middleware is in MIDDLEWARE
4. Check sample rate (OTEL_TRACE_SAMPLE_RATE)

### Logs Not Structured

1. Verify LOG_FORMAT=json in environment
2. Check logging configuration uses StructuredJSONFormatter
3. Verify log aggregator can parse JSON

### Dashboard Shows No Data

1. Verify data source is configured correctly
2. Check time range includes data
3. Verify tenant filter matches existing tenants
4. Check Prometheus has the expected metrics

## Runbook: Common Scenarios

### High Error Rate Alert

1. Check error rate by endpoint: `sum(rate(http_requests_total{status=~"5.."}[5m])) by (endpoint)`
2. Check recent deployments
3. Review error logs: filter by `level=ERROR`
4. Check downstream dependencies (database, cache)

### High Sync Lag Alert

1. Check sync queue depth: `gravitea_sync_queue_depth`
2. Identify affected tenants: `gravitea_sync_lag_seconds` by tenant
3. Check sync worker status
4. Review sync error logs

### Auth Failure Spike

1. Check failure reasons: `gravitea_auth_failures_total` by reason
2. If `rate_limited`: potential brute force attack
3. If `invalid_credentials`: possible credential leak
4. Review security logs for IP patterns

### Database Performance Degradation

1. Check query latency: `db_query_duration_seconds`
2. Identify slow queries by operation
3. Check connection pool status
4. Review database server metrics

## File Structure

```
backend/
├── apps/
│   ├── core/
│   │   ├── health/              # Health check endpoints
│   │   │   ├── __init__.py
│   │   │   ├── urls.py
│   │   │   └── views.py
│   │   ├── logging/             # Structured logging
│   │   │   ├── __init__.py
│   │   │   └── formatters.py
│   │   ├── middleware/
│   │   │   └── trace_middleware.py
│   │   └── observability/       # Metrics infrastructure
│   │       ├── __init__.py
│   │       ├── business_metrics.py
│   │       ├── metrics.py
│   │       └── views.py
│   └── sync/
│       └── logging.py           # Sync-specific logging
├── observability/
│   ├── alerts/                  # Prometheus alert rules
│   │   ├── critical.yml
│   │   ├── warning.yml
│   │   └── business.yml
│   └── dashboards/              # Grafana dashboards
│       ├── overview.json
│       ├── system-metrics.json
│       ├── business-metrics.json
│       └── slo.json
└── OBSERVABILITY.md             # This file
```
