# Quickstart: Rust SSRF Validation Pipeline (SPEC-022)

**Branch**: `022-ssrf-validation-pipeline`
**Prerequisites**: SPEC-017 (Rust Toolchain Bootstrap) complete, `venv-wsl` active

---

## Build

```bash
# From repo root
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP

# Rust build (cargo test)
cd rust/gravitea-core && cargo test && cd ../..

# Maturin develop (install into venv-wsl)
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
    --manifest-path rust/gravitea-core/Cargo.toml --release
```

## Verify Import

```bash
backend/venv-wsl/bin/python -c "
from gravitea_rust import validate_url_safety, check_resolved_ip
print('validate_url_safety:', validate_url_safety('https://example.com/'))
print('check_resolved_ip:', check_resolved_ip('93.184.216.34'))
print('OK — both functions available')
"
```

Expected output:
```
validate_url_safety: (True, 'example.com')
check_resolved_ip: True
OK — both functions available
```

## Run Tests

### Rust-Native Tests

```bash
cd rust/gravitea-core && cargo test -- --nocapture && cd ../..
```

### Python Integration Tests (SPEC-022)

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres \
  venv-wsl/bin/python -m pytest tests/rust_integration/test_security_022.py \
  --tb=short -q --no-header
```

### Existing SSRF Tests (Must Pass Unmodified — SC-010)

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres \
  venv-wsl/bin/python -m pytest tests/security/test_ssrf.py \
  --tb=short -q --no-header
```

### Benchmarks

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres \
  venv-wsl/bin/python -m pytest tests/rust_integration/test_security_022.py \
  -k "benchmark" --tb=short -q --no-header
```

## Docker Validation

```bash
# Build
docker compose build web

# Verify Rust functions available
docker compose run --rm --entrypoint python web -c \
  "from gravitea_rust import validate_url_safety, check_resolved_ip; print('OK')"

# Run security tests in container
docker compose run --rm --entrypoint python web -m pytest \
  tests/security/test_ssrf.py --tb=short -q --override-ini='addopts='

# Run SPEC-022 tests in container
docker compose run --rm --entrypoint python web -m pytest \
  tests/rust_integration/test_security_022.py --tb=short -q --override-ini='addopts='

# Full regression
docker compose run --rm --entrypoint python web -m pytest \
  tests/ --tb=short -q --override-ini='addopts='
```

## Key Files

| File | Purpose |
|------|---------|
| `rust/gravitea-core/src/security.rs` | Rust SSRF validation — 831 lines, 2 exported + 6 internal functions, 58 tests |
| `rust/gravitea-core/src/lib.rs` | Module registration + 2 `#[pymodule_export]` entries |
| `rust/gravitea-core/src/errors.rs` | `SecurityError(String)` variant |
| `rust/gravitea-core/Cargo.toml` | `url = "2.5"` dependency |
| `backend/apps/core/security/ssrf_engine.py` | Python dispatcher (Rust + fallback) — 97 lines |
| `backend/apps/core/security/url_validator.py` | `URLValidator.is_safe()` delegates to `ssrf_engine.is_safe_url()` |
| `backend/gravitea_rust.pyi` | Type stubs: `validate_url_safety`, `check_resolved_ip` |
| `backend/tests/rust_integration/test_security_022.py` | 308 integration tests (83-entry adversarial corpus) |

## Implementation Results

| Metric | Result |
|--------|--------|
| Rust cargo tests | 58 passed (security module) |
| Python integration tests | 308 passed, 1 skipped |
| Adversarial URL corpus | 83 entries (75 unsafe, 8 safe) |
| Docker build | PASS |
| Docker import verification | PASS |
| Docker security tests | 331 passed, 11 skipped |
| Docker SPEC-022 tests | 308 passed, 1 skipped |
| WHATWG divergences | 1 (`http:///path` — Rust url crate vs Python urlparse) |
| IP encoding strategies | 5 (standard, decimal, hex, octal, shortened) |
| Private CIDR ranges | 10 (RFC 1918 + loopback + link-local + This + 4 IPv6) |
| Suspicious hostname patterns | 9 regex + 3 checks (null byte, localhost, IPv6 prefix) |

### Known Divergence

`http:///path` — Rust `url` crate (WHATWG) treats `path` as hostname; Python `urlparse` (RFC-3986) sees empty host. Both correctly block the URL. Handled via `_RUST_PARITY_DIVERGENCES` frozenset with `pytest.skip`.

## Fallback Verification

To test the Python fallback path (when Rust is unavailable):

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres \
  venv-wsl/bin/python -m pytest tests/rust_integration/test_security_022.py \
  -k "fallback" --tb=short -q --no-header
```

## External Test Runner (Token-Optimized)

```bash
# For agent use — delegates to external runner
scripts/run-tests-external.sh -n "022-security" tests/rust_integration/test_security_022.py

# Cargo tests
scripts/run-tests-external.sh -n "022-cargo" "cd rust/gravitea-core && cargo test security -- --nocapture"

# Full regression
scripts/run-tests-external.sh -n "022-regression" --no-cov tests/

# Read results (never read .log in full)
cat Docs/Tests/022-security.summary
cat Docs/Tests/022-security.status
```
