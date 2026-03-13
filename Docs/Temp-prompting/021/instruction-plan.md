# Speckit Context: Observability Hot Path — PLAN Phase (SPEC-021)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: HIGH | **Wave**: 2
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE
> **Predecessors**: SPEC-018 (Crypto), SPEC-019 (Fiscal), SPEC-020 (Data Export) — all committed
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md (no new Django models)

---

## Mission

Design the implementation plan for replacing **24 sequential Python regex operations** with compiled Rust `Regex` objects using `LazyLock<Regex>` (compiled once, reused on every call). These functions — `normalize_path()` and `sanitize_endpoint_label()` — run on **every HTTP request** via the `TraceMiddleware` → `record_request()` call chain.

**Key constraint**: All 24 operations are `re.sub()` replacements, not match-only queries. Each pattern has a unique replacement string. `RegexSet` cannot be used because it only supports match/is_match, not substitution. The correct strategy is `LazyLock<Regex>` per pattern — compiled once at first use, thread-safe, zero recompilation cost.

## Verified Architecture (GitNexus + Source Code Analysis)

### Call Chain

```
TraceMiddleware.__call__()                         # middleware/trace_middleware.py:65
  └─ _record_metrics()                             # middleware/trace_middleware.py:181
       └─ record_request()                         # observability/metrics.py:202
            ├─ normalize_path(endpoint)             # observability/metrics.py:50
            └─ sanitize_endpoint_label(normalized)  # observability/metrics.py:100
```

### Pattern Inventory (24 total)

| Group | Count | Source | Rust Strategy |
|-------|-------|--------|---------------|
| Path Normalizers | 2 | `PATH_NORMALIZERS` list (lines 40-47) | 2 `LazyLock<Regex>` |
| Sensitive Endpoint Patterns | 16 | `SENSITIVE_ENDPOINT_PATTERNS` list (lines 75-97) | 16 `LazyLock<Regex>` with `(?i)` |
| Fallback Substitutions | 6 | Inline `re.sub()` calls (lines 121-131) | 6 `LazyLock<Regex>` with `(?i)` + `\b` |
| **Total** | **24** | | **24 `LazyLock<Regex>` objects** |

### Blast Radius (GitNexus Impact Analysis)

| Direction | Risk | Direct Callers | Processes | Modules |
|-----------|------|----------------|-----------|---------|
| Upstream | **LOW** | 1 (`record_request`) | 1 (`__call__` → `_log_event`) | 2 (Observability, Middleware) |
| Downstream | **LOW** | 0 | 0 | 0 |

### Pre-Resolved Research (from SPECIFY phase)

| Question | Answer | Evidence |
|----------|--------|----------|
| How many regex patterns? | 24 (2 + 16 + 6) | Source code line-by-line count |
| Do any patterns use capture groups? | **NO** — all use simple `re.sub(pattern, replacement, string)` | No `\1`-style backreferences in any pattern |
| RegexSet viable? | **NO** — all operations are substitutions, not match-only | `RegexSet::is_match` can't do replacement |
| Word boundaries needed? | Yes — 6 fallback patterns use `\b` | `\b` supported natively by Rust `regex` crate |
| Case sensitivity? | All 22 sanitization patterns use `re.IGNORECASE` | Use `(?i)` prefix in Rust |
| GIL release needed? | **NO** — sub-microsecond operations; FFI overhead would exceed any GIL contention | ~2-5 microseconds per call |

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements `observability.rs` |
| BACKEND-CODER | backend-architect | Sonnet 4.6 | Creates `observability_engine.py` dispatcher, updates `metrics.py` imports |
| QA | quality-engineer | Sonnet 4.6 | Pattern parity tests, benchmark, regression |

### Sequential-Thinking MCP

- **MANDATORY**: RUST-EXPERT (LazyLock<Regex> architecture, pattern ordering)
- **NOT required**: BACKEND-CODER, QA

## Implementation Phases

### Phase 1: Rust Observability Module (RUST-EXPERT)
- **Risk**: HIGH (pattern parity is non-negotiable)
- Tasks:
  1. Add `regex = "1.10"` to `Cargo.toml` (only new crate needed)
  2. Create `rust/gravitea-core/src/observability.rs`
  3. Implement 24 `LazyLock<Regex>` static objects (2 normalizers + 16 sensitive + 6 fallback)
  4. Implement `normalize_path(path: &str) -> String`:
     - Strip query parameters (split on `?`, take first part)
     - Apply UUID regex replacement → `/{id}`
     - Apply integer ID regex replacement → `/{id}`
  5. Implement `sanitize_endpoint_label(endpoint: &str) -> String`:
     - Apply 16 compiled patterns in order (case-insensitive)
     - Apply 6 fallback word-boundary patterns in order (case-insensitive)
  6. Register `pub mod observability;` in `lib.rs` + `#[pymodule_export]` for both functions
  7. Write Rust-native tests: each of 24 patterns individually + combined scenarios + edge cases (target: ≥20 tests)

### Phase 2: Python Dispatcher (BACKEND-CODER)
- **Risk**: LOW (established pattern from 018/019/020)
- Tasks:
  1. Create `backend/apps/core/observability/observability_engine.py` — dispatcher module:
     - `try: from gravitea_rust import normalize_path, sanitize_endpoint_label`
     - `except ImportError:` → fallback to existing Python functions from `metrics.py`
  2. Update `gravitea_rust.pyi` with type stubs:
     - `def normalize_path(path: str) -> str: ...`
     - `def sanitize_endpoint_label(endpoint: str) -> str: ...`
  3. Modify `record_request()` in `metrics.py` to import from `observability_engine` instead of calling local functions directly
  4. Verify existing Python functions in `metrics.py` remain unchanged (they become the fallback path)

### Phase 3: Quality Validation (QA)
- **Risk**: MEDIUM (must prove exact parity for all 24 patterns)
- Tasks:
  1. Write pattern parity tests in `tests/rust_integration/test_observability_021.py`:
     - Each of 24 patterns tested individually (input → expected output)
     - Combined scenarios (path with UUID + sensitive keyword)
     - Edge cases: empty string, root path, >1000 chars, Unicode, double slashes, `None`
     - Target: ≥50 diverse URL paths
  2. Write fallback tests: simulate missing Rust extension, verify Python fallback produces identical output
  3. Write benchmark: process 1,000 realistic URL paths, assert ≥5x speedup over Python
  4. Add isolated `sanitize_endpoint_label` tests (currently missing from test suite — only `normalize_path` has dedicated tests)

### Phase 4: Docker + Regression (LEAD)
- **Risk**: LOW
- Tasks:
  1. Rebuild Docker image — verify observability functions available in container
  2. Run full test suite — 0 regressions
  3. Run observability-specific tests in container
  4. Update `quickstart.md`

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To | Status |
|----|-------|----------------|-------------|--------|
| R-001 | ~~Capture group classification~~ | ~~RegexSet vs individual Regex~~ | ~~LEAD~~ | **RESOLVED** — No capture groups in any pattern. All 24 use simple `re.sub`. |
| R-002 | LazyLock<Regex> compilation cost | Measure first-call latency for 24 compiled patterns | RUST-EXPERT | OPEN |
| R-003 | Pattern ordering verification | Confirm Rust applies patterns in same order as Python (more specific before less specific) | RUST-EXPERT | OPEN |
| R-004 | Rust `\b` word boundary compatibility with Python `\b` | Verify identical behavior for ASCII word characters | RUST-EXPERT | OPEN |
| R-005 | `re.IGNORECASE` → `(?i)` equivalence for all 22 patterns | Verify no edge cases in case folding | RUST-EXPERT | OPEN |

## Crate Dependencies

| Crate | Version | New/Shared | Purpose |
|-------|---------|-----------|---------|
| `regex` | 1.10 | NEW | Compiled Regex with LazyLock |

## Constraints

1. SPEC-017 must be complete (Rust toolchain bootstrap) — **DONE**
2. All 24 patterns must produce byte-for-byte identical output to Python
3. Pattern application order must match Python list ordering
4. GIL is NOT released (sub-microsecond operations)
5. No Django model changes, no migrations
6. Python fallback mandatory (dispatcher pattern)
7. Test location: `tests/rust_integration/test_observability_021.py` (NOT `tests/unit/observability/`)
8. External test runner for pytest: `scripts/run-tests-external.sh`
9. Maturin build: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release`
10. Error type: `GraviteaError::ComputeError` for validation failures (defined in `errors.rs`)

## Testing Standards

1. **Rust-native**: ≥20 tests — each of 24 patterns individually + combined + edge cases
2. **Python integration**: Pattern parity (identical output for all 50+ test paths)
3. **Isolated sanitization tests**: New tests for `sanitize_endpoint_label` (currently untested in isolation)
4. **Fallback**: Verify Python functions work when Rust unavailable
5. **Benchmark**: ≥5x speedup over Python regex cascade
6. **Docker**: Rebuild and verify in container
7. **Regression**: Full suite 0 new failures

## Existing Test Coverage (Baseline)

Tests that MUST NOT regress (in `tests/unit/observability/test_metrics.py`):
- `test_normalize_uuid_in_path`, `test_normalize_integer_id_in_path`, `test_normalize_multiple_ids_in_path`
- `test_normalize_preserves_path_without_ids`, `test_normalize_handles_query_params`
- `test_normalize_health_endpoints`, `test_normalize_empty_path`
- `test_record_request_normalizes_path`, `test_path_normalization_reduces_cardinality`
- `test_limited_status_code_labels`, `test_limited_method_labels`
- `test_record_request_with_tenant_id`, `test_record_request_without_tenant_id`

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context | Architecture decisions, pattern inventory | `Docs/Temp-prompting/021/instruction-specify.md` |
| Formal spec | User stories, FRs, SCs, edge cases | `specs/021-rust-observability-hotpath/spec.md` |
| Roadmap | OPP-001 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §7 |
| Current metrics | Python implementation (source of truth) | `backend/apps/core/observability/metrics.py` |
| Existing tests | Regression baseline | `backend/tests/unit/observability/test_metrics.py` |
| Trace middleware | Caller chain integration point | `backend/apps/core/middleware/trace_middleware.py` |
| Observability skill | Patterns and conventions | `skills/gravitea-observability/SKILL.md` |
| Crypto dispatcher | Dispatcher pattern reference (018) | `backend/apps/core/encryption/crypto_utils.py` |
| Export dispatcher | Dispatcher pattern reference (020) | `backend/apps/reportes/services/export_engine.py` |
| SPEC-020 plan | Gold standard plan format | `specs/020-rust-data-export/plan.md` |

## Lessons from Previous Specs (Mandatory Patterns)

| Convention | Details | Source |
|-----------|---------|--------|
| Rust module | `pub mod observability;` in `lib.rs` + `#[pyfunction]` + `#[pymodule_export]` + `pub fn` | 018/019/020 |
| Error type | `GraviteaError::ComputeError` for validation failures | 019 |
| Python dispatcher | `observability_engine.py` — `try Rust → except ImportError → fallback Python` | 018/019/020 |
| Test location | `tests/rust_integration/test_observability_021.py` (NOT `tests/unit/observability/`) | 018/019/020 |
| Test DB | Non-Django tests — use `-p no:django` marker or place in `rust_integration/` | 018 |
| `.pyi` stubs | Add type stubs to `gravitea_rust.pyi` for both new functions | 018/019/020 |
| Maturin build | `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release` | 018 |
| External test runner | `scripts/run-tests-external.sh` — agents MUST use this for all pytest | 018/019/020 |
| `pub fn` visibility | `#[pymodule_export]` requires `pub fn` in PyO3 0.28 | 020 |
