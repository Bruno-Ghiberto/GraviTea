# Quickstart: Custom Field Type Validator Acceleration

**Feature Branch**: `025-rust-custom-field-validator`
**Date**: 2026-02-28

## Prerequisites

- Rust 1.93.1+ (`rustup show`)
- Maturin 1.12.4+ (`maturin --version`)
- Python 3.14.3 venv at `backend/venv-wsl/`
- PostgreSQL test instance on port 5433 (`docker compose --profile test up -d postgres-test redis-test`)

## Build & Install

```bash
# From repo root
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP

# Build Rust extension into venv
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml \
  --release

# Verify import
backend/venv-wsl/bin/python -c "from gravitea_rust import validate_custom_fields; print('OK')"
```

## Run Tests

### Rust Unit Tests

```bash
cd rust/gravitea-core
cargo test validation -- --nocapture
```

### Python Integration Tests

```bash
# Using external test runner (preferred)
scripts/run-tests-external.sh "025-tests" "tests/rust_integration/test_custom_fields_025.py"

# Or directly
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres \
  venv-wsl/bin/python -m pytest tests/rust_integration/test_custom_fields_025.py -v
```

### Existing Test Regression

```bash
# All existing custom field tests must pass unchanged (requires postgres-test on port 5433)
cd backend
venv-wsl/bin/python -m pytest \
  tests/core/test_custom_fields_mixin.py \
  tests/core/test_customization_models.py \
  tests/core/test_field_definitions_api.py \
  tests/core/test_cross_entity_validation.py \
  tests/compras/test_custom_fields.py \
  tests/integration/test_custom_fields_e2e.py \
  --tb=short -q
```

## Docker Validation

```bash
# Build
docker compose build web

# Import check
docker compose run --rm --entrypoint python web -c \
  "from gravitea_rust import validate_custom_fields; print('OK')"

# Run SPEC-025 tests in container
docker compose run --rm web bash -c \
  "pip install -r requirements/development.txt && \
   python -m pytest tests/rust_integration/test_custom_fields_025.py -v --override-ini='addopts='"
```

## Key Files

| File | Purpose |
|------|---------|
| `rust/gravitea-core/src/validation.rs` | Rust validator (6 field types) |
| `rust/gravitea-core/src/errors.rs` | `ValidationFieldError` → `PyValueError` |
| `rust/gravitea-core/src/lib.rs` | Module registration |
| `backend/apps/core/serializers/validation_engine.py` | Dispatcher (Rust/Python fallback) |
| `backend/apps/core/serializers/customization.py` | Modified — calls dispatcher |
| `backend/gravitea_rust.pyi` | Type stub |
| `backend/tests/rust_integration/test_custom_fields_025.py` | Integration tests |

## Dispatcher Behavior

| Condition | Path Used |
|-----------|-----------|
| `_USE_RUST=True` and `len(definitions) > 5` | Rust (`validate_custom_fields`) |
| `_USE_RUST=True` and `len(definitions) <= 5` | Python (`_validate_python`) |
| `_USE_RUST=False` (import failed) | Python (`_validate_python`) + warning logged |

## Verification Checklist

- [X] `cargo test validation` — 25 passed (19 validation + 6 other), 0 failed
- [X] `test_custom_fields_025.py` — 31/31 passed (parity, benchmark, edge cases, threshold, fallback)
- [X] Existing custom field tests — 131 passed, 0 failures (SC-004 PASS)
- [X] Docker build — success
- [X] Docker import — `validate_custom_fields` available in container
- [X] Docker SPEC-025 tests — 31/31 passed in 0.38s
- [X] Benchmark: 25 fields < 2ms via Rust path — PASS
