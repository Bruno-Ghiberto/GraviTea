---
name: gravitea-docker
description: >
  Docker containerization patterns for GRAVITEA-ERP including multi-stage builds, compose configurations, and observability stack.
  Trigger: When editing Dockerfile, docker-compose*.yml, or working with containerized deployments.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Docker Skill

Patterns for containerized deployment including multi-stage builds, service orchestration, health checks, and observability infrastructure.

## When to Use

- Creating or modifying Dockerfile configurations
- Working with docker-compose service definitions
- Implementing health check endpoints
- Configuring observability stack (Prometheus, Grafana, Jaeger)
- Setting up test environments with Cloud Run parity
- Managing Docker networks and volumes

---

## Critical Patterns

### Pattern 1: Multi-Stage Dockerfile Build

**Use multi-stage builds to minimize image size and separate build dependencies from runtime.**

```dockerfile
# backend/Dockerfile
# Stage 1: Build - Install dependencies with build tools
FROM python:3.14.3-slim as builder

WORKDIR /app

# Install build dependencies (removed in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production - Minimal runtime image
FROM python:3.14.3-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose application port
EXPOSE 8080

# Health check using Python (no curl in slim image)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')" || exit 1

# Production server with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "gravitea.wsgi:application"]
```

**Key principles:**
- Builder stage: Contains build tools (build-essential, libpq-dev)
- Production stage: Contains only runtime libs (libpq5)
- Virtual environment isolation for clean dependency management
- Non-root user (appuser) for container security
- Python-based health check (slim images don't have curl)

---

### Pattern 2: Core Services Docker Compose

**Define development services with proper networking and health checks.**

```yaml
# backend/docker-compose.yml
services:
  postgres:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: gravitea_dev
      POSTGRES_USER: gravitea
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dev_password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gravitea -d gravitea_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://gravitea:${POSTGRES_PASSWORD:-dev_password}@postgres:5432/gravitea_dev
      - REDIS_URL=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=gravitea.settings.development
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
      - OTEL_SERVICE_NAME=gravitea-backend
      - FIELD_ENCRYPTION_KEY=${FIELD_ENCRYPTION_KEY}
      - BLIND_INDEX_KEY=${BLIND_INDEX_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app  # Development hot-reload
    networks:
      - default
      - gravitea-shared  # External network for observability

volumes:
  postgres_data:
  redis_data:

networks:
  gravitea-shared:
    external: true  # Created manually for cross-compose communication
```

**Key principles:**
- Alpine images for minimal footprint
- Health checks with `service_healthy` conditions
- Environment variables with defaults for development
- Named volumes for data persistence
- External network for observability stack integration

---

### Pattern 3: Test Environment with Cloud Run Parity

**Test environment mirrors Cloud Run production constraints.**

```yaml
# backend/docker-compose.test.yml
services:
  postgres-test:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: gravitea_test
      POSTGRES_USER: gravitea
      POSTGRES_PASSWORD: test_password
    tmpfs:
      - /var/lib/postgresql/data  # RAM-based for speed
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gravitea -d gravitea_test"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis-test:
    image: redis:7-alpine
    tmpfs:
      - /data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  web-test:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://gravitea:test_password@postgres-test:5432/gravitea_test
      - REDIS_URL=redis://redis-test:6379/0
      - DJANGO_SETTINGS_MODULE=gravitea.settings.test
      # Cloud Run parity settings
      - CONN_MAX_AGE=0  # No persistent connections (Cloud Run behavior)
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger-test:4317
      - OTEL_SERVICE_NAME=gravitea-backend-test
    depends_on:
      postgres-test:
        condition: service_healthy
      redis-test:
        condition: service_healthy
    networks:
      - default
      - gravitea-shared

  # Optional services via profiles
  jaeger-test:
    image: jaegertracing/all-in-one:1.54
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
    profiles:
      - observability

  locust-test:
    image: locustio/locust:2.24
    volumes:
      - ./tests/load:/mnt/locust
    command: -f /mnt/locust/locustfile.py --headless -u 10 -r 2
    profiles:
      - load-testing
    depends_on:
      - web-test

networks:
  gravitea-shared:
    external: true
```

**Cloud Run parity settings:**
- `CONN_MAX_AGE=0`: No persistent DB connections (Cloud Run behavior)
- `tmpfs` volumes: RAM-based storage for test speed
- Shorter health check intervals for faster startup
- Profiles for optional services (observability, load-testing)

---

### Pattern 4: Observability Stack

**Full observability infrastructure with Prometheus, Grafana, Jaeger, and Loki.**

```yaml
# backend/docker-compose.observability.yml
services:
  prometheus:
    image: prom/prometheus:v2.49.1
    volumes:
      - ./observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./observability/prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'  # Enable config reload
    ports:
      - "9090:9090"
    networks:
      - gravitea-shared

  grafana:
    image: grafana/grafana:10.3.1
    volumes:
      - ./observability/grafana/provisioning:/etc/grafana/provisioning
      - ./observability/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki
    networks:
      - gravitea-shared

  jaeger:
    image: jaegertracing/all-in-one:1.54
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - SPAN_STORAGE_TYPE=badger
      - BADGER_EPHEMERAL=false
      - BADGER_DIRECTORY_VALUE=/badger/data
      - BADGER_DIRECTORY_KEY=/badger/key
    volumes:
      - jaeger_data:/badger
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    networks:
      - gravitea-shared

  loki:
    image: grafana/loki:2.9.4
    volumes:
      - ./observability/loki/loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    networks:
      - gravitea-shared

  promtail:
    image: grafana/promtail:2.9.4
    volumes:
      - ./observability/promtail/promtail-config.yml:/etc/promtail/config.yml
      - /var/log:/var/log:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    networks:
      - gravitea-shared

  alertmanager:
    image: prom/alertmanager:v0.27.0
    volumes:
      - ./observability/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
    networks:
      - gravitea-shared

volumes:
  prometheus_data:
  grafana_data:
  jaeger_data:
  loki_data:

networks:
  gravitea-shared:
    external: true
```

**Stack components:**
- **Prometheus**: Metrics collection and alerting rules
- **Grafana**: Dashboards and visualization
- **Jaeger**: Distributed tracing with OTLP support
- **Loki + Promtail**: Log aggregation
- **Alertmanager**: Alert routing and notification

---

### Pattern 5: Health Check Endpoint

**Implement health endpoints for Docker and Kubernetes probes.**

```python
# backend/apps/core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_live(request):
    """
    Liveness probe - Is the process running?

    Used by Docker HEALTHCHECK and Kubernetes livenessProbe.
    Should be fast and only check if the process is alive.
    """
    return JsonResponse({"status": "alive"}, status=200)


def health_ready(request):
    """
    Readiness probe - Can the service handle requests?

    Used by Kubernetes readinessProbe and load balancers.
    Checks all critical dependencies.
    """
    checks = {}
    overall_healthy = True

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "unhealthy"
        overall_healthy = False

    # Check Redis cache
    try:
        cache.set("health_check", "ok", timeout=5)
        if cache.get("health_check") == "ok":
            checks["cache"] = "healthy"
        else:
            checks["cache"] = "unhealthy"
            overall_healthy = False
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        checks["cache"] = "unhealthy"
        overall_healthy = False

    status_code = 200 if overall_healthy else 503
    return JsonResponse({
        "status": "ready" if overall_healthy else "not_ready",
        "checks": checks
    }, status=status_code)


def health_startup(request):
    """
    Startup probe - Has the service finished initializing?

    Used by Kubernetes startupProbe. Allows slow-starting containers
    without affecting liveness/readiness checks.
    """
    # Check if migrations are complete
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if plan:
            return JsonResponse({
                "status": "starting",
                "pending_migrations": len(plan)
            }, status=503)

        return JsonResponse({"status": "started"}, status=200)
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        return JsonResponse({
            "status": "error",
            "detail": str(e)
        }, status=503)
```

**URL configuration:**

```python
# backend/gravitea/urls.py
from django.urls import path
from apps.core.views import health_live, health_ready, health_startup

urlpatterns = [
    # Health check endpoints (no authentication required)
    path("health/live", health_live, name="health-live"),
    path("health/ready", health_ready, name="health-ready"),
    path("health/startup", health_startup, name="health-startup"),
    # ... other URLs
]
```

---

### Pattern 6: Network Architecture

**Use external networks for cross-compose communication.**

```bash
# Create the shared network once (before starting any compose)
docker network create gravitea-shared

# Start observability stack (connects to gravitea-shared)
docker compose -f docker-compose.observability.yml up -d

# Start main application (connects to both default and gravitea-shared)
docker compose up -d

# Services can now communicate across compose files via gravitea-shared
# web -> prometheus (for metrics push)
# web -> jaeger (for trace export)
# promtail -> web logs (via docker socket)
```

**Network topology:**

```
┌─────────────────────────────────────────────────────────────┐
│                    gravitea-shared (external)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │prometheus│  │ grafana  │  │  jaeger  │  │   loki   │    │
│  └────▲─────┘  └──────────┘  └────▲─────┘  └────▲─────┘    │
│       │                           │              │          │
│       │ metrics                   │ traces       │ logs     │
│       │                           │              │          │
│  ┌────┴───────────────────────────┴──────────────┴─────┐   │
│  │                        web                           │   │
│  └────┬───────────────────────────┬────────────────────┘   │
└───────┼───────────────────────────┼────────────────────────┘
        │                           │
┌───────┼───────────────────────────┼────────────────────────┐
│       │      default (internal)   │                        │
│  ┌────▼─────┐              ┌──────▼───┐                    │
│  │ postgres │              │  redis   │                    │
│  └──────────┘              └──────────┘                    │
└────────────────────────────────────────────────────────────┘
```

---

## Decision Tree

```
Docker task?
|-- Building image?
|   |-- Production -> Multi-stage build (builder + slim)
|   |-- Development -> Single stage with dev tools
|   +-- Test -> Same as production for parity
|
|-- Defining services?
|   |-- Core (db, cache, app) -> docker-compose.yml
|   |-- Testing -> docker-compose.test.yml with tmpfs
|   |-- Observability -> docker-compose.observability.yml
|   +-- Load testing -> Profile in test compose
|
|-- Health checks?
|   |-- Process alive? -> /health/live (fast, no deps)
|   |-- Ready for traffic? -> /health/ready (check deps)
|   +-- Startup complete? -> /health/startup (migrations)
|
+-- Networking?
    |-- Same compose? -> Use default network
    |-- Cross compose? -> Use gravitea-shared external
    +-- External access? -> Map ports explicitly
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Single-Stage Build with Build Tools

```dockerfile
# FORBIDDEN - Includes build tools in production image
FROM python:3.14.3-slim
RUN apt-get install -y build-essential libpq-dev  # Bloats image!
RUN pip install -r requirements.txt
# Image size: ~800MB

# CORRECT - Multi-stage build
FROM python:3.14.3-slim as builder
RUN apt-get install -y build-essential libpq-dev
RUN pip install -r requirements.txt

FROM python:3.14.3-slim
COPY --from=builder /opt/venv /opt/venv
# Image size: ~200MB
```

### Anti-Pattern 2: Running as Root

```dockerfile
# FORBIDDEN - Security risk
FROM python:3.14.3-slim
COPY . /app
CMD ["gunicorn", "..."]  # Runs as root!

# CORRECT - Non-root user
FROM python:3.14.3-slim
RUN useradd --create-home appuser
USER appuser
CMD ["gunicorn", "..."]
```

### Anti-Pattern 3: No Health Checks

```yaml
# FORBIDDEN - No health checks, depends_on doesn't wait
services:
  web:
    depends_on:
      - postgres  # Starts immediately, may fail!

# CORRECT - Health-based dependency
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
  web:
    depends_on:
      postgres:
        condition: service_healthy
```

### Anti-Pattern 4: Hardcoded Secrets

```yaml
# FORBIDDEN - Secrets in compose file
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: my_secret_password  # Visible in git!

# CORRECT - Environment variable substitution
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # From .env or shell
```

---

## Commands

```bash
# Create shared network (run once)
docker network create gravitea-shared

# Development environment
docker compose up -d
docker compose logs -f web

# Test environment
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml run --rm web-test pytest

# Test with observability
docker compose -f docker-compose.test.yml --profile observability up -d

# Load testing
docker compose -f docker-compose.test.yml --profile load-testing up -d locust-test

# Observability stack
docker compose -f docker-compose.observability.yml up -d

# Full stack (all services)
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Build production image
docker build -t gravitea-backend:latest .
docker build -t gravitea-backend:$(git rev-parse --short HEAD) .

# Check health
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready

# Clean up
docker compose down -v  # Remove volumes too
docker compose -f docker-compose.observability.yml down -v
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | `dev_password` |
| `DATABASE_URL` | Full database connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `DJANGO_SETTINGS_MODULE` | Django settings module | `gravitea.settings.development` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint | - |
| `OTEL_SERVICE_NAME` | Service name for tracing | `gravitea-backend` |
| `FIELD_ENCRYPTION_KEY` | AES-256 encryption key (base64) | - |
| `BLIND_INDEX_KEY` | HMAC key for blind indexes (base64) | - |
| `CONN_MAX_AGE` | Database connection persistence | `0` (Cloud Run) |
| `GRAFANA_PASSWORD` | Grafana admin password | `admin` |

---

## Developer Checklist

Before submitting Docker-related code, verify:

- [ ] Multi-stage build used for production images
- [ ] Non-root user configured in Dockerfile
- [ ] Health checks defined for all services
- [ ] `service_healthy` condition used in depends_on
- [ ] Secrets passed via environment variables, not hardcoded
- [ ] Named volumes for persistent data
- [ ] External network used for cross-compose communication
- [ ] Cloud Run parity settings in test environment (CONN_MAX_AGE=0)
- [ ] tmpfs used for test database (speed)
- [ ] Profiles used for optional services

---

## Resources

- **Dockerfile**: See `backend/Dockerfile`
- **Development Compose**: See `backend/docker-compose.yml`
- **Test Compose**: See `backend/docker-compose.test.yml`
- **Observability Compose**: See `backend/docker-compose.observability.yml`
- **Health Views**: See `backend/apps/core/views.py`
- **Prometheus Config**: See `backend/observability/prometheus/`
- **Grafana Dashboards**: See `backend/observability/grafana/dashboards/`

---

*Last updated: 2026-01-20*
*Components: Dockerfile, docker-compose.yml, docker-compose.test.yml, docker-compose.observability.yml*
