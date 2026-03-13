# Gravitea ERP Test Suite

Comprehensive test suite for the Gravitea ERP backend, organized by test type and functional requirement.

---

## Quick Start

```bash
cd backend

# Install dependencies first
pip install -r requirements/development.txt

# Full test suite with Docker (recommended)
make test

# Quick validation (smoke tests only)
make test-quick

# Unit tests without Docker
make test-unit
```

---

## Commands Reference

This section provides a complete guide to all available test commands. Choose the approach that best fits your needs.

### Makefile Commands (Recommended for Daily Use)

The Makefile provides simple shortcuts for common test scenarios. Run from the `backend/` directory:

| Command | What It Does | When to Use |
|---------|--------------|-------------|
| **Daily Development** | | |
| `make test-unit` | Unit tests without Docker (~1-2 min) | Fast feedback during development |
| `make test-quick` | Smoke tests only (~30 seconds) | Quick validation after changes |
| **Full Validation** | | |
| `make test` | Full test suite with Docker infrastructure | CI/CD, full validation before merge |
| `make test-parallel` | All tests with 4 parallel workers | Faster execution on multi-core machines |
| `make test-coverage` | Coverage-focused run | Checking coverage metrics |
| **Specialized Tests** | | |
| `make test-integration` | Integration tests only | Testing database/API interactions |
| `make test-security` | Security tests only | Security validation before release |
| `make test-load` | Load tests (Locust) | Performance testing |
| `make test-fuzz` | API fuzzing (Schemathesis) | Finding edge cases |
| `make test-property` | Property-based tests (Hypothesis) | Testing invariants |
| **Utilities** | | |
| `make test-no-docker` | All tests without Docker setup | When Docker isn't available |
| `make clean` | Remove test artifacts and caches | Cleaning up after test runs |
| `make help` | Show all available commands | Quick reference |

**Examples:**

```bash
# Daily development workflow
make test-unit          # Fast feedback while coding
make test-quick         # Validate before committing

# Before creating a PR
make test               # Full validation

# After security changes
make test-security      # Validate security tests pass

# Cleanup old reports
make clean
```

### Python Orchestrator (Advanced Usage)

The orchestrator (`scripts/run_tests.py`) provides full control over test execution with Docker lifecycle management.

**Basic Usage:**

```bash
python scripts/run_tests.py [OPTIONS]
```

**Available Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `--quick` | Run smoke tests only | `python scripts/run_tests.py --quick` |
| `--no-docker` | Skip Docker infrastructure setup | `python scripts/run_tests.py --no-docker` |
| `-m MARKERS` | Run specific test markers | `python scripts/run_tests.py -m unit security` |
| `--parallel` | Enable parallel execution | `python scripts/run_tests.py --parallel` |
| `-n NUM` | Number of parallel workers | `python scripts/run_tests.py --parallel -n 8` |
| `--keep-containers` | Don't stop Docker after tests | `python scripts/run_tests.py --keep-containers` |
| `-x` or `--fail-fast` | Stop on first failure | `python scripts/run_tests.py -x` |
| `--coverage-only` | Focus on coverage metrics | `python scripts/run_tests.py --coverage-only` |
| `--help` | Show all available options | `python scripts/run_tests.py --help` |

**Examples:**

```bash
# Full test suite with all features
python scripts/run_tests.py

# Quick smoke tests
python scripts/run_tests.py --quick

# Unit tests only (no Docker needed)
python scripts/run_tests.py --no-docker -m unit

# Multiple markers (unit AND integration)
python scripts/run_tests.py -m unit integration

# Parallel execution with 8 workers
python scripts/run_tests.py --parallel -n 8

# Stop on first failure (useful for debugging)
python scripts/run_tests.py -x

# Keep Docker running after tests (for debugging)
python scripts/run_tests.py --keep-containers

# Security tests only with fail-fast
python scripts/run_tests.py -m security -x
```

### Direct pytest Commands (Manual Control)

For maximum control or debugging, use pytest directly. Note: This bypasses Docker management.

**Basic Format:**

```bash
pytest tests/ [OPTIONS]
```

**Common Commands:**

```bash
# Run all tests with coverage
pytest tests/ -v --cov=apps

# Run specific test file
pytest tests/unit/test_rate_limiter.py -v

# Run specific test function
pytest tests/unit/test_rate_limiter.py::TestRateLimiter::test_rate_limit_exceeded -v

# Run tests by marker
pytest tests/ -m unit -v
pytest tests/ -m "security and not fuzz" -v

# Run with verbose output and stop on first failure
pytest tests/ -v -x

# Run with specific coverage threshold
pytest tests/ --cov=apps --cov-fail-under=90

# Run without coverage (faster)
pytest tests/ -v -p no:cov

# Run with HTML report
pytest tests/ --html=report.html --self-contained-html

# Run specific directory
pytest tests/security/ -v
pytest tests/unit/observability/ -v
```

**Smoke Tests (Special Case):**

Smoke tests require running services and bypass Django:

```bash
# Start services first
docker-compose up -d

# Run smoke tests (bypass Django setup)
pytest tests/smoke/ -v -p no:django --noconftest -o addopts=""

# Strict mode (FAIL instead of skip if services down)
STRICT_MODE=true pytest tests/smoke/test_strict_validation.py -v -p no:django --noconftest -o addopts=""
```

### Which Command Should I Use?

| Scenario | Recommended Command |
|----------|---------------------|
| **During Development** | |
| Quick check while coding | `make test-unit` |
| Validate before committing | `make test-quick` |
| Debugging a specific test | `pytest tests/path/to/test.py::test_name -v -x` |
| Run tests for a specific module | `pytest tests/security/ -v` |
| **Before PR/Merge** | |
| Full validation | `make test` |
| Faster full validation | `make test-parallel` |
| **Specialized Testing** | |
| Security audit | `make test-security` |
| Performance testing | `make test-load` |
| Find edge cases | `make test-fuzz` |
| Test invariants | `make test-property` |
| **CI/CD & Infrastructure** | |
| CI/CD pipeline | `python scripts/run_tests.py` |
| Check coverage metrics | `make test-coverage` |
| Docker not available | `make test-no-docker` |
| Keep Docker after tests | `python scripts/run_tests.py --keep-containers` |

### Understanding Test Output

All test runs generate output in `tests/Logs_report/[timestamp]/`:

```
tests/Logs_report/2026-01-05_15-30-00/
├── test_results.xml       # JUnit XML (for CI/CD)
├── test_report.html       # Visual HTML report (open in browser)
├── test_events.jsonl      # Structured JSON events (for log aggregation)
├── test_run.log           # Plain text execution log
├── pytest.log             # Pytest debug log
├── coverage/              # Coverage HTML report
│   └── index.html         # Open this to see coverage details
├── coverage.json          # Coverage data as JSON
└── run_summary.json       # Orchestrator run metadata
```

A `latest` symlink always points to the most recent run:

```bash
# Open the latest coverage report
open tests/Logs_report/latest/coverage/index.html    # macOS
start tests/Logs_report/latest/coverage/index.html   # Windows
xdg-open tests/Logs_report/latest/coverage/index.html # Linux

# Open the latest HTML test report
open tests/Logs_report/latest/test_report.html
```

---

## Test Organization

```
tests/
├── conftest.py                 # Global fixtures and configuration
├── factories.py                # Factory Boy factories
├── README.md                   # This file
│
├── fixtures/                   # Test data and models
│   ├── docker_models.py        # Docker/health check test data
│   ├── fuzz_models.py          # API fuzzing test configuration
│   ├── load_models.py          # Load testing profiles
│   ├── property_strategies.py  # Hypothesis strategies
│   ├── security.py             # Security test vectors
│   ├── traceability_models.py  # Requirement traceability
│   └── seed_scenarios/         # JSON seed data scenarios
│       ├── minimal.json
│       ├── multi_tenant.json
│       └── standard.json
│
├── plugins/                    # Custom pytest plugins
│   ├── __init__.py
│   └── json_logging.py         # Structured JSON logging for CI/CD
│
├── Logs_report/                # Test output directory
│   └── YYYY-MM-DD_HH-MM-SS/    # Timestamped run directories
│       ├── test_results.xml    # JUnit XML for CI/CD
│       ├── test_report.html    # Visual HTML report
│       ├── test_events.jsonl   # Structured JSON events
│       ├── test_run.log        # Plain text log
│       ├── coverage/           # Coverage HTML report
│       └── run_summary.json    # Orchestrator metadata
│
├── auth/                       # Authentication tests
│   ├── test_authentication.py
│   └── test_users.py
│
├── contract/                   # API contract tests
│   ├── conftest.py
│   ├── test_alertmanager_rules.py
│   ├── test_error_responses.py
│   ├── test_schema_compliance.py
│   └── validators.py
│
├── core/                       # Core module tests
│   ├── test_encryption.py
│   ├── test_fail_closed_security.py
│   ├── test_secrets.py
│   ├── test_security.py
│   ├── test_tenant_isolation.py
│   └── test_validators.py
│
├── docker/                     # Docker integration tests
│   ├── test_database_connections.py
│   ├── test_graceful_shutdown.py
│   ├── test_health_checks.py
│   ├── test_network_topology.py
│   └── test_observability.py
│
├── fuzz/                       # API fuzzing tests (Schemathesis)
│   ├── conftest.py
│   └── test_api_fuzzing.py
│
├── integration/                # Integration tests
│   ├── conftest.py
│   ├── observability/          # Observability integration
│   │   ├── test_business_metrics.py
│   │   ├── test_json_logging.py
│   │   ├── test_metrics_endpoint.py
│   │   └── test_tracing.py
│   ├── test_alerting.py
│   ├── test_auth_contracts.py
│   ├── test_branch_isolation.py
│   ├── test_branch_operations.py
│   ├── test_health_endpoints.py
│   ├── test_inventory_contracts.py
│   ├── test_offline_duration.py
│   ├── test_seed_command.py
│   └── test_trace_propagation.py
│
├── inventario/                 # Inventory module tests
│   ├── test_inventory_api.py
│   ├── test_ml_metadata.py
│   ├── test_stock_movements.py
│   ├── test_stock_service.py
│   └── test_stock_service_robustness.py
│
├── load/                       # Load tests (Locust)
│   ├── locustfile.py
│   ├── test_baseline_performance.py
│   ├── test_peak_handling.py
│   └── test_sustained_load.py
│
├── performance/                # Performance tests
│   ├── test_benchmarks.py
│   └── test_n_plus_one.py
│
├── property/                   # Property-based tests (Hypothesis)
│   ├── test_inventory_boundaries.py
│   ├── test_price_invariants.py
│   └── test_tenant_properties.py
│
├── security/                   # Security tests
│   ├── test_encryption.py
│   ├── test_jwt_attacks.py
│   ├── test_owasp.py
│   ├── test_rate_limiting.py
│   └── test_tenant_isolation.py
│
├── smoke/                      # Smoke tests (real HTTP)
│   ├── conftest.py
│   ├── README.md
│   ├── test_deployment_readiness.py
│   ├── test_e2e_workflows.py
│   ├── test_observability_stack.py
│   └── test_strict_validation.py
│
├── sync/                       # Sync module tests
│   ├── test_conflict_edge_cases.py
│   ├── test_conflict_resolver.py
│   ├── test_retry_logic.py
│   ├── test_sync_endpoints.py
│   ├── test_sync_logging.py
│   └── test_sync_models.py
│
├── tasks/                      # Celery task tests
│   └── test_celery_tasks.py
│
├── traceability/               # Requirement traceability
│   ├── conftest.py
│   ├── test_coverage_report.py
│   └── test_requirement_coverage.py
│
└── unit/                       # Unit tests
    ├── observability/          # Observability unit tests
    │   ├── test_alerts.py
    │   ├── test_business_metrics.py
    │   ├── test_json_logging.py
    │   ├── test_metrics.py
    │   └── test_tracing.py
    ├── test_rate_limiter.py
    ├── test_seed_utils.py
    └── test_trace_correlation.py
```

## Test Markers

| Marker | Description | Command |
|--------|-------------|---------|
| `unit` | Fast unit tests (no external deps) | `pytest -m unit` |
| `integration` | Tests requiring database | `pytest -m integration` |
| `security` | All security tests | `pytest -m security` |
| `owasp` | OWASP Top 10 compliance | `pytest -m owasp` |
| `jwt` | JWT security tests | `pytest -m jwt` |
| `ratelimit` | Rate limiting tests | `pytest -m ratelimit` |
| `encryption` | Encryption/PII tests | `pytest -m encryption` |
| `tenant_isolation` | Multi-tenant isolation | `pytest -m tenant_isolation` |
| `performance` | Performance/N+1 tests | `pytest -m performance` |
| `docker` | Docker integration tests | `pytest -m docker` |
| `load` | Load tests (Locust) | `pytest -m load` |
| `fuzz` | API fuzzing (Schemathesis) | `pytest -m fuzz` |
| `property` | Property-based (Hypothesis) | `pytest -m property` |
| `critical` | Critical path (95% coverage) | `pytest -m critical` |
| `smoke` | Real HTTP requests | See [Smoke Tests](#smoke-tests) |
| `observability` | Observability stack | `pytest -m observability` |
| `strict` | Fail-on-error validation | `pytest -m strict` |
| `traceability` | Requirement traceability | `pytest -m traceability` |
| `slow` | Slow-running tests | `pytest -m slow` |
| `concurrent` | Concurrent operation tests | `pytest -m concurrent` |

### Combining Markers

```bash
# Multiple markers (OR)
python scripts/run_tests.py -m unit integration

# Exclude markers
pytest -m "not slow and not load"

# Combine with expression
pytest -m "security and not fuzz"
```

## Coverage Requirements

| Module Type | Coverage Threshold | Marker |
|-------------|-------------------|--------|
| Standard | 80% | Default |
| Critical Path | 95% | `@pytest.mark.critical` |

### Critical Modules (95% Required)

- `apps.auth` - Authentication/authorization
- `apps.core.encryption` - Data encryption
- `apps.core.middleware` - Security middleware
- `apps.inventario.views` - Inventory API

### Viewing Coverage Reports

```bash
# After running tests (cross-platform)
# macOS
open tests/Logs_report/latest/coverage/index.html

# Windows
start tests/Logs_report/latest/coverage/index.html

# Linux
xdg-open tests/Logs_report/latest/coverage/index.html
```

---

## Specialized Test Types

### Load Tests (Locust)

Load tests validate performance under concurrent user load.

```bash
# Using Makefile
make test-load

# Using orchestrator
python scripts/run_tests.py -m load

# Using Locust CLI directly (for interactive mode)
cd backend
locust -f tests/load/locustfile.py

# Headless mode with specific parameters
locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 5m
#   -u 100  = 100 concurrent users
#   -r 10   = spawn 10 users per second
#   -t 5m   = run for 5 minutes
```

### Security Tests

Security tests cover OWASP Top 10, JWT attacks, rate limiting, and more.

```bash
# All security tests
make test-security

# Or with orchestrator
python scripts/run_tests.py -m security

# Specific security categories
python scripts/run_tests.py -m jwt              # JWT token attacks
python scripts/run_tests.py -m owasp            # OWASP Top 10 compliance
python scripts/run_tests.py -m ratelimit        # Rate limiting validation
python scripts/run_tests.py -m encryption       # Encryption/PII tests
python scripts/run_tests.py -m tenant_isolation # Multi-tenant isolation
```

### API Fuzzing (Schemathesis)

API fuzzing automatically generates malformed requests to find edge cases.

```bash
# Run fuzz tests (longer timeout recommended)
pytest tests/fuzz/ -v -m fuzz --timeout=600

# Or with orchestrator
python scripts/run_tests.py -m fuzz
```

### Property-Based Tests (Hypothesis)

Property-based tests generate random inputs to test invariants.

```bash
# Run property tests
python scripts/run_tests.py -m property

# With specific seed for reproducibility
pytest tests/property/ -v --hypothesis-seed=12345
```

### Smoke Tests (Real HTTP)

Smoke tests make **real HTTP requests** to running services.

```bash
# Start services first
docker-compose up -d

# Using Makefile (recommended)
make test-quick

# Direct pytest (bypass Django setup)
pytest tests/smoke/ -v -p no:django --noconftest -o addopts=""

# Strict mode (FAIL if services down instead of skip)
STRICT_MODE=true pytest tests/smoke/ -v -p no:django --noconftest -o addopts=""
```

See `tests/smoke/README.md` for detailed smoke test documentation.

---

## Functional Requirements Traceability

Tests are mapped to functional requirements (FR-001 through FR-026):

| FR | Description | Test File(s) |
|----|-------------|--------------|
| FR-001 | JWT 1-hour expiration | `test_jwt_attacks.py` |
| FR-002 | JWT RS256 algorithm | `test_jwt_attacks.py` |
| FR-009 | API authentication required | `test_e2e_workflows.py` |
| FR-012 | Security headers | `test_e2e_workflows.py` |
| FR-013 | Health check <200ms | `test_deployment_readiness.py` |
| FR-014 | Readiness checks DB | `test_deployment_readiness.py` |
| FR-018 | Prometheus metrics | `test_observability_stack.py` |
| FR-022 | Malformed input rejected | `test_e2e_workflows.py` |
| FR-024 | 100 concurrent users | `tests/load/` |
| FR-026 | 95% critical coverage | `conftest.py` |

Run traceability report:
```bash
pytest tests/traceability/ -v -m traceability
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SETTINGS_MODULE` | `gravitea.settings.test` | Django settings |
| `BACKEND_URL` | `http://localhost:8000` | Backend API URL |
| `PROMETHEUS_URL` | `http://localhost:9090` | Prometheus URL |
| `GRAFANA_URL` | `http://localhost:3000` | Grafana URL |
| `JAEGER_URL` | `http://localhost:16686` | Jaeger URL |
| `LOKI_URL` | `http://localhost:3100` | Loki URL |
| `STRICT_MODE` | `true` | Fail instead of skip |

## CI/CD Integration

### GitHub Actions Workflows

- **ci.yml** - Main CI: lint, unit, integration, docker tests
- **security-tests.yml** - Security: OWASP, JWT, dependencies
- **load-tests.yml** - Load: Locust performance tests
- **openapi-validation.yml** - OpenAPI spec validation

### CI Pipeline Example

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements/development.txt

      - name: Run tests
        run: python scripts/run_tests.py

      - name: Upload test results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: tests/Logs_report/latest/

      - name: Publish JUnit results
        uses: mikepenz/action-junit-report@v4
        with:
          report_paths: tests/Logs_report/latest/test_results.xml
```

### JSON Log Integration

The `test_events.jsonl` file contains structured events for log aggregation:

```json
{"event": "session_start", "timestamp": "2026-01-05T15:30:00", "session_id": "..."}
{"event": "test_start", "nodeid": "tests/unit/test_example.py::test_func", "timestamp": "..."}
{"event": "test_call", "nodeid": "...", "outcome": "passed", "duration_seconds": 0.05}
{"event": "session_finish", "exit_status": 0, "summary": {"passed": 150, "failed": 0}}
```

## Fixtures

### Global Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `tenant` | Test tenant |
| `tenant_context` | Sets tenant context for test |
| `other_tenant` | Secondary tenant for isolation tests |
| `admin_user` | Admin user with all permissions |
| `sales_user` | Sales user with limited permissions |
| `viewer_user` | Read-only user |
| `authenticated_client` | API client with JWT auth |
| `product` | Test product |
| `branch` | Test branch |
| `product_factory` | Factory for creating products |
| `user_factory` | Factory for creating users |

### Security Fixtures

| Fixture | Description |
|---------|-------------|
| `jwt_attack_vectors` | JWT attack test vectors |
| `rate_limit_test_cases` | Rate limit scenarios |
| `owasp_injection_payloads` | OWASP injection payloads |
| `encryption_test_cases` | Encryption test cases |
| `cross_tenant_test_cases` | Cross-tenant attack scenarios |

### Docker Fixtures

| Fixture | Description |
|---------|-------------|
| `health_check_endpoints` | Health endpoint config |
| `docker_services_config` | Docker services config |
| `expected_network_topology` | Network topology |
| `docker_compose_file` | Path to docker-compose.test.yml |

### Traceability Fixtures

| Fixture | Location |
|---------|----------|
| `traceability_matrix` | `tests/traceability/conftest.py` |
| `functional_requirements` | `tests/traceability/conftest.py` |
| `requirement_test_map` | `tests/conftest.py` |

## Troubleshooting

### Django Setup Errors in Smoke Tests

Smoke tests don't need Django. If you see Django import errors:

```bash
# Use these flags to bypass Django
pytest tests/smoke/ -v -p no:django --noconftest -o addopts=""
```

### Tests Skipping

If tests skip with "Backend not available":

1. Check services: `docker-compose ps`
2. Check backend: `curl http://localhost:8000/health/live`
3. Check logs: `docker-compose logs backend`

### Docker Infrastructure Issues

```bash
# Check Docker health
docker-compose -f docker-compose.test.yml ps

# View container logs
docker-compose -f docker-compose.test.yml logs postgres-test
docker-compose -f docker-compose.test.yml logs redis-test

# Restart infrastructure
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
```

### Coverage Below Threshold

If coverage fails:

1. Check which modules are below threshold
2. Add tests for uncovered code
3. Use coverage report: `open tests/Logs_report/latest/coverage/index.html`

### Hypothesis Tests Slow

Property-based tests can be slow. Limit iterations:

```bash
pytest tests/ -v -m property --hypothesis-seed=0
```

### Plugin Loading Issues

If the JSON logging plugin fails to load:

```bash
# Verify plugin syntax
python -c "import tests.plugins.json_logging"

# Run without plugin
pytest tests/ -p no:tests.plugins.json_logging
```

## Writing New Tests

### Test File Naming

- Unit tests: `test_<module>.py` in `tests/unit/`
- Integration tests: `test_<feature>.py` in `tests/integration/`
- Security tests: `test_<security_area>.py` in `tests/security/`

### Test Function Naming

```python
def test_<what>_<condition>_<expected>():
    """Test description with FR reference."""
    pass

# Examples:
def test_login_invalid_credentials_returns_401():
    """FR-009: Invalid credentials return 401."""
    pass

def test_health_live_responds_under_200ms():
    """FR-013: Health endpoint responds within 200ms."""
    pass
```

### Adding Markers

```python
import pytest

@pytest.mark.security
@pytest.mark.jwt
def test_jwt_algorithm_is_rs256():
    """FR-002: JWT uses RS256 algorithm."""
    pass

@pytest.mark.critical
def test_authentication_required():
    """FR-009: Critical path - requires 95% coverage."""
    pass
```

### Adding to Traceability

Update `tests/fixtures/traceability_models.py`:

```python
REQUIREMENT_TEST_MAP = {
    "FR-001": ["tests/security/test_jwt_attacks.py::test_jwt_expiration"],
    "FR-002": ["tests/security/test_jwt_attacks.py::test_jwt_algorithm"],
    # Add new mappings here
}
```

## Latest Test Results

**Run Date:** January 21, 2026

| Metric | Value |
|--------|-------|
| Tests Collected | 1,713 |
| Tests Passed | 1,675 |
| Tests Failed | 0 |
| Tests Skipped | 38 |
| Coverage | 80.13% |
| Docker Setup Time | 14.9s |
| Pytest Execution Time | 519.5s |

Test reports are available in `tests/Logs_report/latest/`.

---

## Dependencies

Required packages (in `requirements/development.txt`):

```
pytest>=8.0,<9.0
pytest-django>=4.8,<5.0
pytest-cov>=4.1,<5.0
pytest-asyncio>=0.23,<0.24
pytest-timeout>=2.3,<3.0
pytest-html>=4.1,<5.0
pytest-xdist>=3.5,<4.0
factory_boy>=3.3,<4.0
hypothesis>=6.100,<7.0
schemathesis>=3.25,<4.0
locust>=2.20,<3.0
docker>=7.0,<8.0
testcontainers>=4.0,<5.0
```

Install all test dependencies:

```bash
pip install -r requirements/development.txt
```
