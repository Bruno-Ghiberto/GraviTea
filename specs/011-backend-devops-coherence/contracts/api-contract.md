# API Contract: Backend Coherence & DevOps Master Plan

**Branch**: `011-backend-devops-coherence` | **Date**: 2026-02-15

This feature introduces one new API endpoint (health check). All other changes are infrastructure-level (Docker, settings, SQL scripts) with no API surface changes.

---

## New Endpoint: Health Check

### `GET /api/v1/health/`

**Purpose**: Verify backend readiness — database connectivity, migration status, cache availability.

**Authentication**: None (public endpoint for Docker health checks and load balancer probes).

**Request**: No parameters.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "checks": {
    "database": {
      "status": "up",
      "latency_ms": 2.3
    },
    "cache": {
      "status": "up",
      "latency_ms": 0.8
    },
    "migrations": {
      "status": "up",
      "pending": 0
    }
  },
  "version": "0.1.2",
  "timestamp": "2026-02-15T14:30:00Z"
}
```

**Response (503 Service Unavailable)**:
```json
{
  "status": "unhealthy",
  "checks": {
    "database": {
      "status": "down",
      "error": "connection refused"
    },
    "cache": {
      "status": "up",
      "latency_ms": 0.8
    },
    "migrations": {
      "status": "unknown"
    }
  },
  "version": "0.1.2",
  "timestamp": "2026-02-15T14:30:00Z"
}
```

**Rules**:
- Returns 200 only if ALL checks pass
- Returns 503 if ANY check fails
- Individual check statuses: `up`, `down`, `unknown`
- `latency_ms` measured via simple ping query (DB: `SELECT 1`, Redis: `PING`)
- `migrations.pending` counts unapplied migrations via `MigrationExecutor`
- `version` from `settings.VERSION` or package metadata
- No PII in response (satisfies Constitution Principle IX)
- No authentication required (satisfies Docker health check use case)

**Docker Integration**:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health/')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

---

## Existing Endpoints: No Changes

The following existing endpoint groups are unchanged by this feature:

| Module | Base Path | Status |
|--------|-----------|--------|
| Auth | `/api/v1/auth/` | No changes |
| Core | `/api/v1/core/` | No changes |
| Facturacion | `/api/v1/facturacion/` | No changes |
| Inventario | `/api/v1/inventario/` | No changes |
| Ventas | `/api/v1/ventas/` | No changes |
| Sync | `/api/v1/sync/` | No changes |
| Schema | `/api/v1/schema/` | No changes |

---

## Existing Endpoint: Metrics (Validation Only)

### `GET /metrics/`

**Purpose**: Prometheus scrape target. Already implemented in `apps/core/observability/`.

**This feature**: Validates that the endpoint is reachable from the Prometheus container via the shared Docker network. No code changes to the endpoint itself.

**Validation criteria**:
- Prometheus scrapes `gravitea-web:8080/metrics/` successfully
- Response contains `django_http_requests_total` counter
- Response contains `django_http_request_duration_seconds` histogram
- Response contains business metrics (if any API calls have been made)

---

## OpenAPI Schema Impact

The health endpoint will be added to the OpenAPI schema via drf-spectacular:

```yaml
paths:
  /api/v1/health/:
    get:
      operationId: health_check
      summary: System health check
      tags:
        - health
      security: []  # No authentication required
      responses:
        '200':
          description: All systems healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthCheck'
        '503':
          description: One or more systems unhealthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthCheck'
```
