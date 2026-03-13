# GRAVITEA-ERP Observability Stack - Advanced Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GRAVITEA BACKEND                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │   metrics   │  │   logging   │  │   tracing   │                         │
│  │   .py       │  │   .py       │  │   .py       │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                │                │                                 │
│    /metrics         JSON stdout      OTLP gRPC                             │
└─────────┼────────────────┼────────────────┼─────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │  PROMETHEUS  │ │   PROMTAIL   │ │    JAEGER    │
   │  :9090       │ │   :9080      │ │   :16686     │
   │  (PULL)      │ │   (PUSH)     │ │   (PUSH)     │
   └──────┬───────┘ └──────┬───────┘ └──────────────┘
          │                │                │
          │                ▼                │
          │         ┌──────────────┐        │
          │         │     LOKI     │        │
          │         │   :3100      │        │
          │         └──────────────┘        │
          │                │                │
          ▼                ▼                ▼
   ┌─────────────────────────────────────────────┐
   │                  GRAFANA                     │
   │                  :3000                       │
   │     [Metrics]  [Logs]  [Traces]             │
   └─────────────────────────────────────────────┘
          │
          ▼
   ┌──────────────┐
   │ ALERTMANAGER │ → Slack / PagerDuty
   │   :9093      │
   └──────────────┘
```

## The Three Pillars of Observability

| Pillar | Tool | Data Type | Query Language |
|--------|------|-----------|----------------|
| **Metrics** | Prometheus | Time-series numbers | PromQL |
| **Logs** | Loki + Promtail | Structured text | LogQL |
| **Traces** | Jaeger | Request spans | Trace ID lookup |

---

## 1. PROMETHEUS - Metrics Collection

**Purpose**: Time-series database for numerical measurements using the RED pattern.

### Implementation Files

| File | Purpose |
|------|---------|
| `apps/core/observability/metrics.py` | RED metrics: request rate, errors, duration |
| `apps/core/observability/business_metrics.py` | Domain metrics: orders, inventory, sync, auth |
| `apps/core/observability/views.py` | `/metrics` endpoint for Prometheus scraping |
| `observability/prometheus.yml` | Prometheus scrape configuration |

### Key Metrics Defined

```python
# RED Metrics (metrics.py:66-86)
http_requests_total            # Counter - total requests by method/endpoint/status/tenant
http_request_duration_seconds  # Histogram - latency with buckets [0.01...10s]
http_requests_in_progress      # Gauge - concurrent requests

# Business Metrics (business_metrics.py)
orders_total                   # Counter - by tenant/branch/status
order_value_total              # Counter - monetary value
sync_queue_depth               # Gauge - pending sync operations
sync_processing_lag_seconds    # Gauge - oldest pending operation age
auth_attempts_total            # Counter - login attempts
auth_failures_total            # Counter - failed logins by reason
inventory_movements_total      # Counter - stock movements
low_stock_alerts               # Gauge - products below threshold
```

### Metric Types Explained

| Type | Description | Example |
|------|-------------|---------|
| **Counter** | Only increases (resets on restart) | `http_requests_total` |
| **Gauge** | Can increase or decrease | `sync_queue_depth` |
| **Histogram** | Samples in buckets for percentiles | `http_request_duration_seconds` |

### Path Normalization (Cardinality Control)

```python
# metrics.py:40-59
# Prevents metric explosion from UUIDs/IDs in paths
/api/v1/products/550e8400-e29b-41d4-a716-446655440000/
    → /api/v1/products/{id}/

/api/v1/branches/123/products/
    → /api/v1/branches/{id}/products/
```

### Usage Examples

```python
from apps.core.observability.metrics import record_request
from apps.core.observability.business_metrics import (
    record_order,
    record_inventory_movement,
    update_sync_lag,
    record_auth_attempt,
    record_auth_failure,
)

# In middleware/view - record HTTP request
record_request(
    method="POST",
    endpoint="/api/v1/orders/",
    status_code=201,
    duration=0.045,
    tenant_id="tenant-123"
)

# In business logic - record order
record_order(
    tenant_id="tenant-123",
    branch_id="branch-456",
    status="completed",
    amount=150.00,
    currency="CRC"
)

# Record inventory movement
record_inventory_movement(
    tenant_id="tenant-123",
    operation="sale",
    branch_id="branch-456",
    product_type="beverage",
    quantity=5
)

# Update sync metrics
update_sync_lag(tenant_id="tenant-123", lag_seconds=5.2)

# Record authentication events
record_auth_attempt(tenant_id="tenant-123", method="password")
record_auth_failure(tenant_id="tenant-123", reason="invalid_credentials")
```

### PromQL Query Examples

```promql
# Error rate percentage (last 5 minutes)
100 * sum(rate(http_requests_total{status_code=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))

# Error rate by tenant
sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (tenant_id)
  / sum(rate(http_requests_total[5m])) by (tenant_id)

# P99 latency (99th percentile)
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# P99 latency by tenant
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, tenant_id)
)

# Request rate per second by endpoint
sum(rate(http_requests_total[1m])) by (endpoint)

# Sync queue building up? (positive derivative = growing)
deriv(sync_queue_depth[5m]) > 0

# Average request duration
rate(http_request_duration_seconds_sum[5m])
  / rate(http_request_duration_seconds_count[5m])

# Top 5 slowest endpoints
topk(5,
  sum(rate(http_request_duration_seconds_sum[5m])) by (endpoint)
    / sum(rate(http_request_duration_seconds_count[5m])) by (endpoint)
)
```

### Prometheus Configuration

```yaml
# observability/prometheus.yml
global:
  scrape_interval: 15s      # How often to scrape targets
  evaluation_interval: 15s  # How often to evaluate alert rules

scrape_configs:
  - job_name: 'gravitea-backend'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
```

---

## 2. ALERTMANAGER - Alert Routing

**Purpose**: Receives alerts from Prometheus, deduplicates, groups, and routes to notification channels.

### Alert Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Prometheus    │     │  Alertmanager   │     │   Receivers     │
│                 │     │                 │     │                 │
│ Rule evaluates  │────▶│ Receives alert  │────▶│ Slack           │
│ every 15s       │     │ Groups by labels│     │ PagerDuty       │
│                 │     │ Deduplicates    │     │ Email           │
│ If threshold    │     │ Routes by match │     │ Webhook         │
│ exceeded for    │     │ Waits intervals │     │                 │
│ `for` duration  │     │ Sends notif     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Timing Parameters Explained

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `group_wait` | 30s | Buffer time before first notification |
| `group_interval` | 5m | Wait before sending updates to same group |
| `repeat_interval` | 4h | Re-notify interval if alert still firing |

### Routing Configuration

| Severity | Team | group_wait | repeat_interval | Channel |
|----------|------|------------|-----------------|---------|
| `critical` | platform | 10s | 1h | #alerts-critical |
| `warning` | varies | 30s | 4h | #alerts-{team} |
| `info` | business | 5m | 8h | #alerts-business |

### Inhibition Rules (Alert Suppression)

```yaml
# alertmanager.yml:149-162
# If critical fires, suppress warning for same alert+tenant
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'tenant_id']

  # If critical or warning fires, suppress info
  - source_match_re:
      severity: 'critical|warning'
    target_match:
      severity: 'info'
    equal: ['alertname', 'tenant_id']
```

### SLO-Based Alerts

| Alert | Condition | Duration | Severity | SLO Target |
|-------|-----------|----------|----------|------------|
| `HighErrorRate` | >1% 5xx errors | 5m | critical | 99% availability |
| `HighErrorRateGlobal` | >1% 5xx (all tenants) | 5m | critical | 99% availability |
| `HighLatencyP99` | P99 >500ms | 5m | warning | <500ms latency |
| `CriticalLatencyP99` | P99 >2s | 2m | critical | <2s max |
| `SyncQueueLagHigh` | >60s lag | 5m | warning | <60s sync |
| `SyncQueueLagCritical` | >5min lag | 2m | critical | - |
| `SyncQueueDepthHigh` | >1000 pending | 10m | warning | - |
| `HealthCheckFailure` | backend down | 1m | critical | - |
| `DatabaseConnectionPoolExhausted` | >90% pool used | 5m | warning | - |
| `AuthFailureSpike` | >30% auth failures | 5m | warning | security |
| `NoOrdersReceived` | 0 orders (business hours) | 30m | info | business |

### Alert Rule Example

```yaml
# observability/alerts/slo_alerts.yml
- alert: HighErrorRate
  expr: |
    (
      sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (tenant_id)
      /
      sum(rate(http_requests_total[5m])) by (tenant_id)
    ) > 0.01
  for: 5m
  labels:
    severity: critical
    slo: availability
    team: platform
  annotations:
    summary: "High error rate detected for tenant {{ $labels.tenant_id }}"
    description: |
      Error rate is {{ printf "%.2f" (mulf $value 100) }}% (threshold: 1%).
    runbook_url: "https://docs.gravitea.com/runbooks/high-error-rate"
```

---

## 3. LOKI - Log Aggregation

**Purpose**: Cost-effective log storage with label-based indexing (not full-text like Elasticsearch).

### Key Concept: Labels vs Content

```
Labels (indexed, fast filtering):
  {tenant_id="123", level="ERROR", logger="views"}

Content (not indexed, grep-style search):
  "Product created successfully for order #12345"
```

**Why this matters**: Query by labels first (fast), then filter content (slower).

### Configuration Highlights

| Setting | Value | Purpose |
|---------|-------|---------|
| `retention_period` | 168h (7 days) | Auto-delete old logs |
| `ingestion_rate_mb` | 10 | Max 10MB/s ingest per tenant |
| `ingestion_burst_size_mb` | 20 | Burst allowance |
| `max_entries_limit_per_query` | 10000 | Query safety limit |
| `max_query_parallelism` | 32 | Concurrent query execution |
| `chunk_idle_period` | 1h | Flush chunks after idle |

### LogQL Query Examples

```logql
# All logs for a tenant
{tenant_id="tenant-123"}

# Errors only
{tenant_id="tenant-123", level="ERROR"}

# Errors containing "database"
{tenant_id="tenant-123", level="ERROR"} |= "database"

# Errors NOT containing "timeout"
{tenant_id="tenant-123", level="ERROR"} != "timeout"

# Regex match
{job="gravitea-django"} |~ "order.*failed"

# Parse JSON and filter by field
{job="gravitea-django"} | json | status_code >= 500

# Slow requests (duration > 1 second)
{job="gravitea-django"} | json | duration_ms > 1000

# Count errors per logger (last hour)
sum(count_over_time({level="ERROR"}[1h])) by (logger)

# Error rate per minute
sum(rate({level="ERROR"}[1m]))

# Top 10 error messages
topk(10, sum by (message) (count_over_time({level="ERROR"} | json [1h])))
```

### Log Stream Selection

```logql
# By job name
{job="gravitea-django"}

# By multiple labels
{job="gravitea-django", level="ERROR", tenant_id="tenant-123"}

# Label regex
{job=~"gravitea.*"}

# Exclude label value
{job="gravitea-django", level!="DEBUG"}
```

---

## 4. PROMTAIL - Log Shipping

**Purpose**: Discovers logs, parses/transforms them, ships to Loki.

### Scrape Jobs Configured

| Job | Source | Discovery Method |
|-----|--------|------------------|
| `docker-gravitea` | Container stdout | Docker socket SD |
| `django-logs` | `/app/logs/*.json` | Static file path |
| `access-logs` | `/app/logs/access*.log` | Static file path |
| `system-logs` | `/var/log/*.log` | Static file path |

### Pipeline Stages Explained

```yaml
pipeline_stages:
  # 1. Parse JSON structure
  - json:
      expressions:
        timestamp: timestamp
        level: level
        logger: logger
        message: message
        trace_id: trace_id
        tenant_id: tenant_id

  # 2. Set log timestamp from parsed field
  - timestamp:
      source: timestamp
      format: RFC3339Nano

  # 3. Promote fields to Loki labels (indexed)
  - labels:
      level:
      logger:
      tenant_id:
      trace_id:

  # 4. Use message field as the log line
  - output:
      source: message
```

### Expected JSON Log Schema

```json
{
  "@timestamp": "2025-12-05T10:30:00.123456789Z",
  "level": "INFO",
  "logger": "apps.inventario.views",
  "message": "Product created successfully",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "a1b2c3d4e5f67890",
  "tenant_id": "tenant-123",
  "branch_id": "branch-456",
  "user_id": "user-789",
  "request_path": "/api/v1/products/",
  "request_method": "POST",
  "status_code": 201,
  "duration_ms": 45,
  "extra": {}
}
```

### Label Cardinality Warning

**DO index**: `level`, `logger`, `tenant_id`, `job`
**DON'T index**: `trace_id`, `user_id`, `request_path` (high cardinality)

High-cardinality labels cause Loki performance issues. Use structured metadata or log line content for high-cardinality data.

---

## 5. JAEGER - Distributed Tracing

**Purpose**: Visualize request flow through spans, debug latency issues.

### Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `OTEL_TRACING_ENABLED` | `false` (default) | Enable/disable tracing |
| `OTEL_SERVICE_NAME` | `gravitea-backend` | Service identifier |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Jaeger collector |
| `OTEL_SAMPLING_RATIO` | `0.1` (10%) | Head-based sampling rate |

### Sampling Strategy

```python
# tracing.py configuration
sampling_ratio: 0.1    # 10% of requests sampled
sample_errors: True    # 100% of errors always sampled
```

### Usage in Code

```python
from apps.core.observability.tracing import (
    create_span,
    set_span_error,
    add_span_attribute,
)

# Create a span for a specific operation
with create_span("process_order", attributes={"order_id": "123"}) as span:
    try:
        # Your business logic
        items = fetch_order_items()

        if span:
            add_span_attribute(span, "items_count", len(items))

        result = calculate_total(items)

        if span:
            add_span_attribute(span, "total", result)

    except Exception as e:
        set_span_error(span, e)
        raise

# Nested spans
with create_span("checkout_flow") as parent_span:
    with create_span("validate_cart") as child_span:
        validate()
    with create_span("process_payment") as child_span:
        charge()
    with create_span("send_confirmation") as child_span:
        notify()
```

### Sensitive Data Scrubbing

```python
# Automatically redacted patterns (tracing.py:264-273)
SENSITIVE_PATTERNS = {
    "password", "passwd", "secret", "token",
    "api_key", "apikey", "access_token", "refresh_token",
    "credit_card", "card_number", "cvv",
    "ssn", "social_security", "private_key"
}

# SQL statement scrubbing
"SELECT * FROM users WHERE email = 'john@example.com' AND id = 123"
    → "SELECT * FROM users WHERE email = ? AND id = ?"
```

### Trace Correlation

The `trace_id` from your existing `TraceContext` is converted to OpenTelemetry format:

```python
# UUID to OTEL trace_id conversion
UUID: 550e8400-e29b-41d4-a716-446655440000
  → Remove dashes: 550e8400e29b41d4a716446655440000
  → Parse as hex: int("550e8400e29b41d4a716446655440000", 16)
  → 128-bit integer for OTEL
```

This enables clicking `trace_id` in Grafana/Loki → jumping directly to Jaeger trace view.

---

## 6. GRAFANA - Unified Dashboard

**Purpose**: Single UI to query Prometheus, Loki, and Jaeger with correlated views.

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Jaeger | http://localhost:16686 | - |
| Alertmanager | http://localhost:9093 | - |
| Loki | http://localhost:3100 | - |

### Pre-Built Dashboards

| Dashboard | File | Purpose |
|-----------|------|---------|
| Overview | `dashboards/overview.json` | Service health, error rates, latency |
| System Metrics | `dashboards/system-metrics.json` | CPU, memory, request throughput |
| SLO Tracking | `dashboards/slo.json` | Error budgets, latency percentiles |
| Business Metrics | `dashboards/business-metrics.json` | Orders, inventory, sync status |

### Cross-Signal Investigation Workflow

```
1. Notice error rate spike in Grafana dashboard (Prometheus)
       │
       ▼
2. Click time range to zoom in
       │
       ▼
3. Switch to Logs panel, filter: {level="ERROR", time=selected_range}
       │
       ▼
4. Find error log with trace_id
       │
       ▼
5. Click trace_id → Opens Jaeger
       │
       ▼
6. See full request flow, identify slow/failing span
       │
       ▼
7. Fix the issue with full context
```

### Data Source Configuration

Grafana automatically connects to:
- **Prometheus**: `http://prometheus:9090` (metrics)
- **Loki**: `http://loki:3100` (logs)
- **Jaeger**: `http://jaeger:16686` (traces)

---

## 7. LOGGING - Structured JSON Logs

**Purpose**: Produce ELK/Loki-compatible logs with trace correlation.

### Configuration

```python
# In Django settings
from apps.core.observability.logging import get_logging_config

LOGGING = get_logging_config(
    log_level="INFO",    # or from LOG_LEVEL env var
    log_format="json",   # or from LOG_FORMAT env var
)
```

### Features

| Feature | Implementation |
|---------|---------------|
| JSON Format | `JSONLogFormatter` class |
| Trace Correlation | `TraceCorrelationFilter` injects trace_id, tenant_id |
| Sensitive Data Scrubbing | `SensitiveDataFilter` redacts passwords, tokens |
| Async Logging | Optional queue-based handler for non-blocking |

### Log Output Example

```json
{
  "@timestamp": "2025-12-05T10:30:00.123456+00:00",
  "level": "INFO",
  "logger": "apps.inventario.views",
  "message": "Product created successfully",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant-123",
  "branch_id": "branch-456",
  "user_id": "user-789",
  "request_path": "/api/v1/products/",
  "request_method": "POST",
  "status_code": 201,
  "duration_ms": 45,
  "extra": {
    "product_sku": "BEV-001"
  }
}
```

### Sensitive Data Auto-Redaction

```python
# These keys are automatically redacted in logs:
SENSITIVE_KEYS = {
    "password", "passwd", "secret", "token",
    "api_key", "apikey", "access_token", "refresh_token",
    "authorization", "credit_card", "card_number", "cvv",
    "ssn", "social_security", "private_key"
}

# Input
{"user": "john", "password": "secret123", "token": "abc"}

# Output (logged)
{"user": "john", "password": "[REDACTED]", "token": "[REDACTED]"}
```

---

## Quick Start

### Start the Observability Stack

```bash
# Navigate to backend directory
cd backend

# Start all observability services
docker-compose -f docker-compose.observability.yml up -d

# Verify services are running
docker-compose -f docker-compose.observability.yml ps
```

### Verify Each Component

```bash
# 1. Check Django metrics endpoint
curl http://localhost:8000/metrics

# 2. Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 3. Check Prometheus can query
curl 'http://localhost:9090/api/v1/query?query=up'

# 4. Check Loki is ready
curl http://localhost:3100/ready

# 5. Check Alertmanager status
curl http://localhost:9093/api/v2/status

# 6. Open Grafana
open http://localhost:3000  # Login: admin/admin

# 7. Open Jaeger
open http://localhost:16686
```

### Enable Tracing (Optional)

```bash
# Set environment variables before starting Django
export OTEL_TRACING_ENABLED=true
export OTEL_SERVICE_NAME=gravitea-backend
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SAMPLING_RATIO=0.1
```

### Test Alert Firing

```bash
# Simulate high error rate (for testing)
for i in {1..100}; do
  curl -s http://localhost:8000/api/v1/nonexistent/ > /dev/null
done

# Check firing alerts
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'

# Check Alertmanager received it
curl http://localhost:9093/api/v2/alerts | jq '.'
```

---

## Troubleshooting

### Metrics Not Appearing in Prometheus

```bash
# 1. Check metrics endpoint works
curl http://localhost:8000/metrics

# 2. Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health, lastError}'

# 3. Common issue: DisallowedHost
# Fix: Add to ALLOWED_HOSTS in Django settings
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'host.docker.internal']
```

### Logs Not Appearing in Loki

```bash
# 1. Check Promtail is running
docker logs gravitea-promtail

# 2. Check Promtail can reach Loki
docker exec gravitea-promtail wget -q -O- http://loki:3100/ready

# 3. Check Docker socket is mounted
docker exec gravitea-promtail ls -la /var/run/docker.sock

# 4. Verify log format is JSON
docker logs gravitea-backend 2>&1 | head -1 | jq .
```

### Traces Not Appearing in Jaeger

```bash
# 1. Verify tracing is enabled
echo $OTEL_TRACING_ENABLED  # Should be "true"

# 2. Check Jaeger collector is reachable
curl http://localhost:14269/  # Health endpoint

# 3. Check OTLP endpoint
curl http://localhost:4317  # Should refuse connection (gRPC)

# 4. Verify sampling ratio isn't 0
echo $OTEL_SAMPLING_RATIO  # Default: 0.1 (10%)
```

### Alerts Not Firing

```bash
# 1. Check rule syntax
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name, health, lastError}'

# 2. Check if metrics exist for the rule
curl 'http://localhost:9090/api/v1/query?query=http_requests_total'

# 3. Check Alertmanager connection
curl http://localhost:9090/api/v1/alertmanagers

# 4. Reload Prometheus config after rule changes
curl -X POST http://localhost:9090/-/reload
```

### High Cardinality Warnings

```bash
# Check metric cardinality
curl 'http://localhost:9090/api/v1/label/__name__/values' | jq '. | length'

# Find high-cardinality metrics
curl 'http://localhost:9090/api/v1/status/tsdb' | jq '.data.seriesCountByMetricName | to_entries | sort_by(-.value) | .[0:10]'
```

---

## Best Practices

### Metrics

1. **Use path normalization** - Replace IDs with `{id}` to prevent cardinality explosion
2. **Limit label values** - Avoid unbounded labels like user_id in metrics
3. **Use histograms for latency** - Enables percentile calculations
4. **Name metrics clearly** - `<namespace>_<name>_<unit>` (e.g., `http_request_duration_seconds`)

### Logs

1. **Use structured JSON** - Enables efficient parsing and querying
2. **Include trace_id** - Enables correlation with traces
3. **Index carefully** - Only index low-cardinality fields as Loki labels
4. **Scrub sensitive data** - Use filters to redact PII

### Traces

1. **Sample appropriately** - 10% for normal traffic, 100% for errors
2. **Add meaningful attributes** - Include business context (order_id, tenant_id)
3. **Scrub sensitive data** - Never trace passwords, tokens, PII
4. **Name spans descriptively** - `process_order`, `validate_inventory`, not `step1`

### Alerts

1. **Set appropriate thresholds** - Based on SLOs, not arbitrary numbers
2. **Use `for` duration** - Avoid alerting on transient spikes
3. **Include runbook URLs** - Help on-call engineers respond quickly
4. **Use inhibition rules** - Prevent alert storms during incidents

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_FORMAT` | `json` | Log output format (`json` or `text`) |
| `LOG_LEVEL` | `INFO` | Minimum log level |
| `OTEL_TRACING_ENABLED` | `false` | Enable OpenTelemetry tracing |
| `OTEL_SERVICE_NAME` | `gravitea-backend` | Service name in traces |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Jaeger collector endpoint |
| `OTEL_SAMPLING_RATIO` | `0.1` | Trace sampling ratio (0.0-1.0) |
| `DJANGO_ENV` | `development` | Environment tag for traces |

---

## Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Django | 8000 | HTTP | Application + `/metrics` endpoint |
| Prometheus | 9090 | HTTP | Metrics database + UI |
| Grafana | 3000 | HTTP | Visualization dashboards |
| Loki | 3100 | HTTP | Log aggregation API |
| Jaeger UI | 16686 | HTTP | Trace visualization |
| Jaeger OTLP | 4317 | gRPC | Trace ingestion (gRPC) |
| Jaeger OTLP | 4318 | HTTP | Trace ingestion (HTTP) |
| Alertmanager | 9093 | HTTP | Alert routing + UI |
| Promtail | 9080 | HTTP | Log agent metrics |
