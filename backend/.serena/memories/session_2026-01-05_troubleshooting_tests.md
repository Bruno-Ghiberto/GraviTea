# Session: Test Troubleshooting and Performance Fixes
**Date**: 2026-01-05
**Branch**: 005-debug-testing-docker

## Summary
Fixed critical test performance issues causing 32+ minute test runs. Root cause was port mismatch and missing health checks for web-test container.

## Root Causes Identified

### 1. Port Mismatch (Critical)
- **Problem**: Smoke tests expected `http://localhost:8000` but docker-compose.test.yml mapped web-test to port 8001
- **Impact**: Each HTTP request timeout = 10s, causing cascade slowdown
- **Fix**: Updated `tests/smoke/conftest.py` defaults to port 8001

### 2. Missing web-test Health Check
- **Problem**: Orchestrator only waited for postgres-test and redis-test
- **Impact**: Tests started before backend was ready
- **Fix**: Added web-test container check + HTTP endpoint verification

## Files Modified

### tests/smoke/conftest.py
- Changed `BACKEND_URL` default from `http://localhost:8000` → `http://localhost:8001`
- Changed `PROMETHEUS_URL` default from `http://localhost:9090` → `http://localhost:9091`
- Updated both `get_service_endpoints()` and `backend_url` fixture

### scripts/run_tests.py
- Added `web-test` to health check services (60 retries × 2s)
- Added `_verify_http_endpoint()` method for HTTP-level health verification
- Better error handling with warnings instead of hard failures

## Test Suite Statistics
| Marker | Count | Docker Required |
|--------|-------|-----------------|
| unit | 183 | No |
| integration | 29 | Yes |
| security | 184 | Yes |
| smoke | 53 | Yes |
| docker | 111 | Yes |
| property | 51 | Yes |
| load | 70 | Yes |
| fuzz | 45 | Yes |
| traceability | 65 | Yes |
| TOTAL | ~1508 | Mixed |

## Recommended Test Strategy
1. `make test-unit` - Quick validation (15s, no Docker)
2. `python scripts/run_tests.py -m "integration or security" --fail-fast` - Staged Docker tests
3. `make test` - Full suite (expected 5-10 min after fixes)

## Previous Session Context
- Test orchestration system created (`scripts/run_tests.py`)
- Custom pytest JSON logging plugin created
- Makefile with test shortcuts created
- Fixed: coverage threshold, hypothesis profile warning, TestReference rename, Unicode encoding

## Pending Verification
- Run `make test` to confirm fixes work
- Some security tests may still fail if they need live API responses
