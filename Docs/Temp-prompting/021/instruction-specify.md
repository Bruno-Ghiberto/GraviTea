# Speckit Context: Observability Hot Path (SPEC-021)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: HIGH | **Wave**: 2
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE
> **Predecessors**: SPEC-018 (Crypto), SPEC-019 (Fiscal Compute), SPEC-020 (Data Export) — all committed

---

## Mission Statement

Replace the `normalize_path()` and `sanitize_endpoint_label()` functions in `backend/apps/core/observability/metrics.py` with Rust implementations using compiled `Regex` objects. These functions run on **every HTTP request** and currently execute **25 sequential regex operations** — the highest-frequency Rust candidate in the codebase.

## Why This Matters Now

- **Every HTTP request** triggers this code path via the `TraceMiddleware` → `record_request()` call chain
- **25 regex operations** per request (2 path normalizers + 17 sensitive-endpoint patterns + 6 fallback substitutions) → compiled Regex cascade in Rust
- **5-15x speedup** on regex cascade. At 1000 req/s, saves ~2-5ms of CPU per second
- **Trivial FFI boundary**: One `&str` in, one `String` out — no serialization overhead
- **Pure functions**: No Django ORM, no DB, no side effects — ideal Rust candidates
- **Zero downstream dependencies**: Both functions are leaf nodes (confirmed via GitNexus impact analysis)

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Crate | `regex 1.10` | Standard Rust regex with lazy compilation support |
| Compilation strategy | `LazyLock<Regex>` per pattern (compiled once, reused) | Avoids recompilation per call; thread-safe static initialization |
| GIL handling | NOT released | Sub-microsecond operations; FFI overhead would exceed any GIL contention |
| Input/Output | `&str` → `String` | Trivial boundary, zero serialization overhead |
| Fallback | Python regex functions via dispatcher | Existing implementation stays as fallback per project convention |
| Dispatcher pattern | `observability_engine.py` (try Rust → fallback Python) | Consistent with `crypto_utils.py`, `fiscal_compute.py`, `export_engine.py` |

## Current State (What Exists Today)

### Verified Call Chain (GitNexus)

```
TraceMiddleware.__call__()                         # middleware/trace_middleware.py:65
  └─ _record_metrics()                             # middleware/trace_middleware.py:181
       └─ record_request()                         # observability/metrics.py:202
            ├─ normalize_path(endpoint)             # observability/metrics.py:50
            └─ sanitize_endpoint_label(normalized)  # observability/metrics.py:100
```

### Function 1: `normalize_path()` — lines 50-66

**Purpose**: Collapse dynamic path segments (UUIDs, integer IDs) to `{id}` to prevent Prometheus label cardinality explosion.

**Pattern inventory** (2 compiled `re.Pattern` objects in `PATH_NORMALIZERS`):

| # | Pattern | Replacement | Example |
|---|---------|-------------|---------|
| 1 | UUID v4 (`/[0-9a-f]{8}-...{12}`) | `/{id}` | `/products/550e8400-.../details` → `/products/{id}/details` |
| 2 | Integer ID (`/\d+`) | `/{id}` | `/branches/123/products/` → `/branches/{id}/products/` |

**Additional logic**: Strips query parameters (`?` and everything after) before pattern matching.

### Function 2: `sanitize_endpoint_label()` — lines 100-131

**Purpose**: Redact sensitive keywords from endpoint paths to prevent exposure of tokens, passwords, and credentials in Prometheus labels.

**Pattern inventory** (17 compiled `re.Pattern` objects in `SENSITIVE_ENDPOINT_PATTERNS` + 6 inline fallback `re.sub` calls):

| # | Category | Pattern | Replacement |
|---|----------|---------|-------------|
| 1 | Password | `/password[-_]?reset/?` | `/auth-action/` |
| 2 | Password | `/change[-_]?password/?` | `/auth-action/` |
| 3 | Password | `/reset[-_]?password/?` | `/auth-action/` |
| 4 | Password | `/forgot[-_]?password/?` | `/auth-action/` |
| 5 | Token | `/token/[^/]+/?` | `/auth/{redacted}/` |
| 6 | Token | `/token/?` | `/auth/` |
| 7 | Token | `/refresh[-_]?token/?` | `/auth-refresh/` |
| 8 | API Key | `/api[-_]?key/[^/]+/?` | `/key/{redacted}/` |
| 9 | API Key | `/api[-_]?key/?` | `/key/` |
| 10 | Secret | `/secret/[^/]+/?` | `/{redacted}/` |
| 11 | Secret | `/secret/?` | `/{redacted}/` |
| 12 | Credential | `/credential/[^/]+/?` | `/{redacted}/` |
| 13 | Credential | `/credential/?` | `/{redacted}/` |
| 14 | Key | `/private[-_]?key/?` | `/{redacted}/` |
| 15 | Verify | `/verify/[^/]+/?` | `/verify/{redacted}/` |
| 16 | Activate | `/activate/[^/]+/?` | `/activate/{redacted}/` |
| 17 | — | (no 17th compiled; total compiled = 16 above) | — |

**Fallback substitutions** (6 inline `re.sub` calls with word boundaries):

| # | Word | Replacement | Flags |
|---|------|-------------|-------|
| F1 | `\bpassword\b` | `auth` | IGNORECASE |
| F2 | `\bsecret\b` | `redacted` | IGNORECASE |
| F3 | `\btoken\b` | `auth` | IGNORECASE |
| F4 | `\bapi[_-]?key\b` | `key` | IGNORECASE |
| F5 | `\bprivate[_-]?key\b` | `redacted` | IGNORECASE |
| F6 | `\bcredential\b` | `redacted` | IGNORECASE |

**Total operations per request**: 2 (normalize) + 16 (sensitive compiled) + 6 (fallback) = **24 regex operations**.

### Blast Radius (GitNexus Impact Analysis)

| Direction | Risk | Direct | Processes | Modules |
|-----------|------|--------|-----------|---------|
| Upstream (what depends on these) | **LOW** | 1 (`record_request`) | 1 (`__call__` → `_log_event`) | 2 (Observability, Middleware) |
| Downstream (what these depend on) | **LOW** | 0 | 0 | 0 |

**Existing test coverage** (7 tests for `normalize_path`, 6 tests for `record_request`/cardinality):
- `test_normalize_uuid_in_path`, `test_normalize_integer_id_in_path`, `test_normalize_multiple_ids_in_path`
- `test_normalize_preserves_path_without_ids`, `test_normalize_handles_query_params`
- `test_normalize_health_endpoints`, `test_normalize_empty_path`
- `test_record_request_normalizes_path`, `test_path_normalization_reduces_cardinality`
- `test_limited_status_code_labels`, `test_limited_method_labels`
- `test_record_request_with_tenant_id`, `test_record_request_without_tenant_id`

No existing tests for `sanitize_endpoint_label` in isolation — the speckit MUST generate these.

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
├── lib.rs              # Add observability submodule + re-exports
└── observability.rs    # NEW — normalize_path, sanitize_endpoint_label
```

### New Python Dispatcher

```
backend/apps/core/observability/
└── observability_engine.py   # NEW — try Rust → fallback Python
```

### Functions to Implement

| Function | Rust Signature | Python Fallback |
|----------|---------------|-----------------|
| `normalize_path` | `fn normalize_path(path: &str) -> String` | Existing `metrics.py:normalize_path` |
| `sanitize_endpoint_label` | `fn sanitize_endpoint_label(endpoint: &str) -> String` | Existing `metrics.py:sanitize_endpoint_label` |

### Integration Point

`record_request()` in `metrics.py` currently calls the Python functions directly. After implementation, it MUST call the dispatcher module instead:

```python
# Before (current)
from apps.core.observability.metrics import normalize_path, sanitize_endpoint_label

# After (target)
from apps.core.observability.observability_engine import normalize_path, sanitize_endpoint_label
```

The existing Python functions REMAIN in `metrics.py` unchanged — they become the fallback path.

### Cargo.toml Additions

```toml
regex = "1.10"
```

## FFI Boundary Analysis

| Input | Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|------|-------------|-------------|-----------|----------|
| ~50 char URL path | ~50 bytes | ~0.1μs | ~20-50μs (24 regex ops) | ~2-5μs (compiled DFA) | **+15-45μs** |

## Critical Caveats

1. **Pattern parity is non-negotiable**: Every Python regex pattern MUST produce identical output through Rust. Extract all 24 patterns and write 1:1 equivalence tests.
2. **Case-insensitive matching**: All 16 compiled patterns + all 6 fallback patterns use `re.IGNORECASE`. In Rust, use `(?i)` prefix or `RegexBuilder::case_insensitive(true)`.
3. **Word boundaries**: The 6 fallback patterns use `\b`. Rust's `regex` crate supports `\b` natively — verify behavior matches Python's `\b` for ASCII word characters.
4. **Query parameter stripping**: `normalize_path` splits on `?` before regex matching. The Rust implementation must replicate this.
5. **Ordering matters**: `sanitize_endpoint_label` applies compiled patterns first, then fallback patterns. The order within each group also matters — e.g., `/token/[^/]+` before `/token/` (more specific first).
6. **No capture groups needed**: All patterns use `re.sub(pattern, replacement, string)` — none use `\1`-style backreferences. Simple string replacement is sufficient.

## Success Criteria

1. `cargo test` passes with ≥20 observability tests covering all 24 patterns individually + combined scenarios
2. Pattern parity: every Python regex produces identical output through Rust for a corpus of ≥50 test paths
3. Benchmark shows ≥5x speedup over Python regex cascade on the test corpus
4. Isolated `sanitize_endpoint_label` tests are added (currently missing from test suite)
5. Fallback works without Rust extension (dispatcher pattern)
6. Docker image builds with observability functions available
7. Full test suite passes with 0 regressions
8. `record_request()` integration works end-to-end through dispatcher

## Lessons from Previous Specs (018, 019, 020)

These patterns are **mandatory** — do not deviate:

| Convention | Details |
|-----------|---------|
| Rust module | `pub mod observability;` in `lib.rs` + `#[pyfunction]` + `#[pymodule_export]` + `pub fn` |
| Error type | Use `GraviteaError::ComputeError` for any validation failures (defined in `errors.rs`) |
| Python dispatcher | `observability_engine.py` — try `from gravitea_rust import fn` → except `ImportError` → fallback |
| Test location | `tests/rust_integration/test_observability_021.py` (NOT `tests/unit/observability/`) |
| Test DB | These are non-Django tests — use `-p no:django` marker or place in `rust_integration/` |
| Backward compat | Python callers MUST NOT change behavior — dispatcher returns identical types |
| `.pyi` stubs | Add type stubs to `gravitea_rust.pyi` for both new functions |
| Maturin build | `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release` |

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | OPP-001 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §7 |
| Acceleration opps | Deep analysis | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
| Current metrics | Python implementation | `backend/apps/core/observability/metrics.py` |
| Observability skill | Patterns and conventions | `skills/gravitea-observability/SKILL.md` |
| SPEC-020 (gold standard) | Reference spec format | `specs/020-rust-data-export/spec.md` |
| Existing tests | Regression baseline | `backend/tests/unit/observability/test_metrics.py` |
| Trace middleware | Integration point | `backend/apps/core/middleware/trace_middleware.py` |
| Crypto dispatcher | Dispatcher pattern reference | `backend/apps/core/encryption/crypto_utils.py` |
| Export dispatcher | Dispatcher pattern reference | `backend/apps/reportes/services/export_engine.py` |
