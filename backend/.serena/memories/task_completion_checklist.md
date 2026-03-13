# Gravitea ERP - Task Completion Checklist

## Before Marking Task Complete

### 1. Code Quality Checks
```bash
# Format code
black apps/ tests/
isort apps/ tests/

# Lint
flake8 apps/ tests/

# Type check (if modifying typed code)
mypy apps/
```

### 2. Testing

**Using Makefile (Recommended):**
```bash
# Quick validation during development
make test-unit          # Unit tests only (~1-2 min)
make test-quick         # Smoke tests (~30 sec)

# Full validation before PR
make test               # Full suite with Docker
make test-parallel      # Faster on multi-core

# Specialized tests
make test-security      # Security tests
make test-integration   # Integration tests
make test-coverage      # Coverage focus
```

**Using Orchestrator (Advanced):**
```bash
python scripts/run_tests.py                    # Full suite
python scripts/run_tests.py --quick            # Smoke tests
python scripts/run_tests.py -m unit security   # Specific markers
python scripts/run_tests.py --parallel -n 8    # 8 parallel workers
python scripts/run_tests.py -x                 # Stop on first failure
```

**Direct pytest (Debugging):**
```bash
pytest tests/path/to/test.py::test_name -v -x  # Specific test
pytest tests/ -m unit -v                        # By marker
pytest tests/ --cov=apps --cov-fail-under=80   # Coverage check
```

### 3. Security Considerations
- [ ] No hardcoded secrets or credentials
- [ ] PII fields use encrypted field types
- [ ] Tenant isolation maintained (using TenantBoundManager)
- [ ] Input validation present where needed
- [ ] No SQL injection risks (use ORM)

### 4. Documentation
- [ ] Docstrings added for new classes/functions
- [ ] `help_text` on model fields
- [ ] API schema regenerated if endpoints changed:
  ```bash
  python manage.py spectacular --file openapi-generated.yaml
  ```

### 5. Migrations (if models changed)
```bash
# Create migrations
python manage.py makemigrations

# Verify migrations are correct
python manage.py showmigrations

# Test migrations apply cleanly
python manage.py migrate
```

### 6. Git Hygiene
- [ ] Changes committed to feature branch (not main)
- [ ] Descriptive commit message
- [ ] No unrelated files included
- [ ] No temporary/debug code left in

## Quick Validation Commands

```bash
# All-in-one quality check (with new Makefile)
black apps/ tests/ && isort apps/ tests/ && flake8 apps/ tests/ && make test-unit

# Full validation before PR
make test
```

## Test Output Location

All test runs generate output in `tests/Logs_report/[timestamp]/`:
- `test_results.xml` - JUnit XML for CI/CD
- `test_report.html` - Visual HTML report
- `coverage/index.html` - Coverage report

Open latest coverage:
```bash
# Windows
start tests/Logs_report/latest/coverage/index.html

# macOS
open tests/Logs_report/latest/coverage/index.html

# Linux
xdg-open tests/Logs_report/latest/coverage/index.html
```

## Markers for Test Categories
When writing tests, use appropriate markers:
- `@pytest.mark.unit` - Fast, no external dependencies
- `@pytest.mark.integration` - Requires database
- `@pytest.mark.security` - Security tests (OWASP, JWT, etc.)
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.property` - Hypothesis property tests
- `@pytest.mark.load` - Locust load tests
- `@pytest.mark.fuzz` - Schemathesis API fuzzing
- `@pytest.mark.smoke` - Real HTTP requests to services
- `@pytest.mark.critical` - Requires 95% coverage

## Common Issues to Check
1. **Missing tenant context**: Tests need `tenant_context` fixture
2. **Missing imports**: Circular imports in models
3. **Serializer validation**: Test both valid and invalid inputs
4. **Permissions**: Verify endpoints require authentication
5. **Pagination**: Large querysets should be paginated

## Current Branch Status: 005-debug-testing-docker

**Completed:**
- [x] Test orchestration system (`scripts/run_tests.py`)
- [x] Custom pytest JSON logging plugin
- [x] Makefile with 12 test targets
- [x] pytest.ini configuration
- [x] Fixture conflict resolution
- [x] Comprehensive tests/README.md
- [x] Fixed smoke test port mismatch (8000 → 8001)
- [x] Added web-test health checks to orchestrator
- [x] Added HTTP endpoint verification before tests

**Session 2026-01-05 Fixes:**
- Port configuration in `tests/smoke/conftest.py`
- Health check improvements in `scripts/run_tests.py`
- Test run time reduced from 32+ min to expected 5-10 min

**Next Phase:**
- Verify `make test` runs successfully with fixes
- GitHub Actions CI/CD integration
- Review any remaining security test failures
