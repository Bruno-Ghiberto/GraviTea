# Smoke Tests - Real Integration Testing

These tests validate that the backend is **actually working** by making real HTTP requests to running services.

## Key Difference from Unit Tests

| Unit Tests | Smoke Tests |
|------------|-------------|
| Use mocks and fixtures | Make REAL HTTP requests |
| Pass even if services are down | FAIL if services are down |
| Test code logic | Test deployment readiness |
| Run in CI without services | Require running services |

## Test Categories

### 1. Deployment Readiness (`test_deployment_readiness.py`)
- FR-013: Health endpoints respond within 200ms
- FR-014: Readiness checks database connectivity
- Validates all health endpoints work

### 2. Observability Stack (`test_observability_stack.py`)
- FR-018: Prometheus metrics exposed
- Grafana dashboards accessible
- Jaeger tracing functional
- Loki log aggregation ready

### 3. E2E Workflows (`test_e2e_workflows.py`)
- FR-009: Authentication required
- FR-012: Security headers present
- FR-022: Malformed input rejected
- Complete API workflow validation

### 4. Strict Validation (`test_strict_validation.py`)
- **FAILS** (not skips) when services are down
- Use for deployment gates
- Comprehensive deployment status report

## Running Tests

### Prerequisites
```bash
# Start all services
docker-compose up -d

# For full observability testing
docker-compose -f docker-compose.observability.yml up -d
```

### Run Smoke Tests
```bash
# All smoke tests (requires -p no:django to avoid Django setup)
# From backend directory:
pytest tests/smoke/ -v -p no:django --noconftest -o addopts=""

# Or from tests/smoke directory:
cd tests/smoke
pytest . -v -p no:django --noconftest -o addopts=""

# Strict mode (FAIL if services down)
STRICT_MODE=true pytest tests/smoke/test_strict_validation.py -v -p no:django --noconftest -o addopts=""

# Integration tests only
pytest tests/smoke/ -v -m integration -p no:django --noconftest -o addopts=""

# Observability tests
pytest tests/smoke/ -v -m observability -p no:django --noconftest -o addopts=""
```

### Important Notes
- Smoke tests make **REAL HTTP requests** and don't use Django's test client
- Use `-p no:django --noconftest -o addopts=""` to bypass Django setup
- Tests will fail/error when services aren't running (this is expected behavior)

### Environment Variables
```bash
BACKEND_URL=http://localhost:8000     # Backend API
PROMETHEUS_URL=http://localhost:9090  # Prometheus
GRAFANA_URL=http://localhost:3000     # Grafana
JAEGER_URL=http://localhost:16686     # Jaeger
LOKI_URL=http://localhost:3100        # Loki
STRICT_MODE=true                      # Fail instead of skip
```

## Test Markers

- `@pytest.mark.smoke` - All smoke tests
- `@pytest.mark.integration` - Integration tests requiring services
- `@pytest.mark.observability` - Observability stack tests
- `@pytest.mark.strict` - Tests that fail (not skip) on errors

## CI/CD Integration

### Pre-deployment Check
```yaml
# .github/workflows/deploy.yml
- name: Run Smoke Tests
  env:
    BACKEND_URL: ${{ secrets.STAGING_URL }}
    STRICT_MODE: "true"
  run: pytest tests/smoke/test_strict_validation.py -v
```

### Post-deployment Validation
```yaml
- name: Validate Deployment
  run: |
    pytest tests/smoke/test_deployment_readiness.py -v
    pytest tests/smoke/test_e2e_workflows.py -v
```

## Troubleshooting

### Tests Skipping
If tests skip with "Backend not available":
1. Ensure services are running: `docker-compose ps`
2. Check backend logs: `docker-compose logs backend`
3. Verify URL: `curl http://localhost:8000/health/live`

### Tests Failing
If strict tests fail:
1. Check deployment status in test output
2. Verify database connectivity
3. Check observability stack if testing metrics

## Example Output

```
STRICT DEPLOYMENT VALIDATION REPORT
======================================================================
✅ backend              http://localhost:8000/health/live
✅ prometheus           http://localhost:9090/-/healthy
✅ grafana              http://localhost:3000/api/health
❌ jaeger               http://localhost:16686/
   └── Error: Connection refused
======================================================================
Result: 3/4 services healthy
======================================================================
```
