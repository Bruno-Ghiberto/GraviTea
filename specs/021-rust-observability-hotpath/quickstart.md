# Quick Start: Rust Observability Hot Path (SPEC-021)

**Branch**: `021-rust-observability-hotpath`
**Prerequisite**: SPEC-017 (Rust toolchain) must be complete

## What This Spec Does

Replaces 24 sequential Python regex operations in `normalize_path()` and `sanitize_endpoint_label()` with compiled Rust `Regex` objects using `LazyLock<Regex>`. These functions run on every HTTP request via the TraceMiddleware.

## Files Changed/Created

### New Files

| File | Purpose |
|------|---------|
| `rust/gravitea-core/src/observability.rs` | Rust implementation — 24 compiled regex patterns |
| `backend/apps/core/observability/observability_engine.py` | Python dispatcher — try Rust, fallback Python |
| `backend/tests/rust_integration/test_observability_021.py` | Integration tests — pattern parity, benchmark, fallback |

### Modified Files

| File | Change |
|------|--------|
| `rust/gravitea-core/Cargo.toml` | Add `regex = "1.10"` |
| `rust/gravitea-core/src/lib.rs` | Add `mod observability;` + 2 `#[pymodule_export]` |
| `backend/gravitea_rust.pyi` | Add type stubs for 2 new functions |
| `backend/apps/core/observability/metrics.py` | Update `record_request()` to import from dispatcher |

## Build & Test

### 1. Build Rust Extension

```bash
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

### 2. Run Rust Tests

```bash
cd rust/gravitea-core
cargo test observability -- --nocapture
```

### 3. Run Python Integration Tests

```bash
scripts/run-tests-external.sh "021-obs" \
  "backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_observability_021.py -v --tb=short -q"
```

### 4. Run Existing Observability Tests (Regression)

```bash
scripts/run-tests-external.sh "021-regression" \
  "backend/venv-wsl/bin/python -m pytest backend/tests/unit/observability/test_metrics.py -v --tb=short -q"
```

### 5. Docker Verification

```bash
docker compose build web
docker compose run --rm --entrypoint python web -c \
  "from gravitea_rust import normalize_path, sanitize_endpoint_label; print('OK')"
```

## Architecture

```
TraceMiddleware.__call__()
  └─ _record_metrics()
       └─ record_request()                    # metrics.py
            ├─ normalize_path(endpoint)        # FROM observability_engine.py
            └─ sanitize_endpoint_label(norm)   # FROM observability_engine.py

observability_engine.py:
  try:
    from gravitea_rust import normalize_path, sanitize_endpoint_label  # Rust
  except ImportError:
    from .metrics import normalize_path, sanitize_endpoint_label  # Python fallback
```

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Regex strategy | `LazyLock<Regex>` per pattern (24 statics) | All ops are `re.sub`, not match-only; RegexSet can't substitute |
| GIL release | NOT released | Sub-microsecond ops; FFI overhead would exceed GIL contention |
| Case insensitivity | `(?i)` prefix in Rust patterns | Equivalent to Python's `re.IGNORECASE` for ASCII |
| Word boundaries | `\b` in Rust regex | Compatible with Python's `\b` for ASCII keywords |
| Error type | `GraviteaError::ComputeError` | Consistent with SPEC-019 convention |

## Verification Checklist

- [x] `cargo test observability` passes with 38 tests (target: 20+)
- [x] Pattern parity: all 24 patterns produce identical output to Python (76 parity tests)
- [x] Benchmark: 1,000 paths processed — see actual speedup below
- [x] Fallback: Python functions work when Rust unavailable (13 fallback tests)
- [x] Existing tests: 24 observability tests in `test_metrics.py` pass unchanged
- [x] Docker: both functions importable and correct in container
- [x] Full suite: 0 SPEC-021 regressions (2410 passed in Docker)

## Actual Benchmark Results

| Function | Python (1K paths) | Rust (1K paths) | Speedup |
|----------|-------------------|-----------------|---------|
| `normalize_path` (2 patterns) | ~0.003s | ~0.003s | ~1.0x |
| `sanitize_endpoint_label` (22 patterns) | ~0.008s | ~0.003s | ~2.6x |
| Combined pipeline | ~0.011s | ~0.005s | ~2.4x |

**SC-001 note**: The original 5x target was not met. Root cause: Python's `re` module
is a C extension — the baseline is already compiled C code, not pure Python.
Per-call PyO3 FFI overhead (~0.3-0.5us) dominates for sub-microsecond regex ops.
Rust still provides: (1) guaranteed O(1) startup via `LazyLock` pre-compilation,
(2) elimination of per-request regex compilation risk, (3) 2.6x speedup on the
heavier `sanitize_endpoint_label` path with 22 patterns.
