# Quickstart: ARCA CAEA Batch Builder Acceleration

**Branch**: `024-rust-arca-batch` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Prerequisites

- Rust 1.93.1 (`rustup show`)
- Maturin 1.12.4 (`maturin --version`)
- Python 3.14.3 WSL venv (`backend/venv-wsl/`)
- Docker Compose (`docker compose version`)

## Build & Test

### 1. Rust compilation

```bash
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
cargo test --manifest-path rust/gravitea-core/Cargo.toml 2>&1 | tail -40
```

### 2. Install into Python venv

```bash
VIRTUAL_ENV=$(pwd)/backend/venv-wsl backend/venv-wsl/bin/maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

### 3. Verify import

```bash
backend/venv-wsl/bin/python -c "from gravitea_rust import build_caea_batch_request; print('OK')"
```

### 4. Run integration tests

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres PYTHONPATH=. \
  venv-wsl/bin/python -m pytest tests/rust_integration/test_arca_024.py \
  --confcutdir=tests/rust_integration --tb=short -q --no-cov
```

**Note**: `--confcutdir=tests/rust_integration` is required to isolate from the root conftest's autouse `set_rls_tenant_context` fixture which depends on PostgreSQL. SPEC-024 tests are pure computation and do not need a database.

### 5. Docker validation

```bash
docker compose build web
docker compose run --rm --entrypoint python web -c \
  "from gravitea_rust import build_caea_batch_request; print('OK')"
```

## Test Results (2026-02-28)

### Cargo Tests
- **21 tests** in `rust/gravitea-core/src/arca.rs` — all PASS
- Covers: basic comprobante, service dates, IVA (single/multi), tributos (guard), CbtesAsoc (CUIT fallback), defaults, large batch, negative imp_trib, large floats

### Pytest Integration Tests
- **40 tests** in `tests/rust_integration/test_arca_024.py` — all PASS

| Test Class | Count | Description |
|------------|-------|-------------|
| TestUS1Integration | 10 | 50 comprobantes, key names (ImpIVA/CAEA), structure, floats, defaults |
| TestUS4Parity | 17 | Rust vs Python produce identical output for all scenarios |
| TestUS2Threshold | 6 | Batch <=10 → Python, >10 → Rust routing |
| TestUS3Fallback | 6 | `_USE_RUST=False` → correct output, warning logged |
| TestBenchmark | 1 | 50 comprobantes (IVA+tributos) via Rust < 5ms (SC-001 PASS) |

### Regression
- **0 new failures** from SPEC-024 changes
- 248 other rust_integration tests pass (excluding 172 pre-existing SPEC-022 + import-order failures)

### Docker
- **BLOCKED**: Docker Desktop not running during test session. Requires manual validation.

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `rust/gravitea-core/src/arca.rs` | NEW | Serde structs + `build_caea_batch_request` (~824 lines) |
| `rust/gravitea-core/src/errors.rs` | MODIFY | +`ARCABuildError` variant |
| `rust/gravitea-core/src/lib.rs` | MODIFY | +`mod arca` + pymodule_export |
| `backend/apps/facturacion/arca/caea_engine.py` | NEW | Dispatcher (Rust/Python fallback, 122 lines) |
| `backend/apps/facturacion/arca/caea.py` | MODIFY | Replace inner loop with dispatcher call |
| `backend/gravitea_rust.pyi` | MODIFY | +1 function stub (`build_caea_batch_request`) |
| `backend/tests/rust_integration/test_arca_024.py` | NEW | 40 tests (parity + threshold + fallback + benchmark) |

## Key Decisions

- Zero new Cargo dependencies (chrono, rust_decimal eliminated)
- String passthrough for dates (no parsing/validation)
- `str::parse::<f64>()` for amounts (matches Python `float()`)
- Threshold: >10 comprobantes → Rust path
- GIL released during batch construction via `py.detach()`
- Two ALL-CAPS serde renames: `ImpIVA`, `CAEA`
- `--confcutdir=tests/rust_integration` needed for pytest (avoids root conftest DB dependency)
